"""SSH communication client."""

import asyncio
import time
from typing import Any, Dict, Optional, List
from loguru import logger
import paramiko


class SSHClient:
    """Client for communicating with feeder over SSH."""

    # Buffer size for reading responses
    BUFFER_SIZE = 4096
    
    # Maximum number of commands in queue
    MAX_QUEUE_SIZE = 100
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize SSH client.
        
        Args:
            config: Client configuration from communication.yaml
        """
        self._config = config
        self._connected = False
        
        # Extract SSH config
        ssh_config = config["communication"]["hardware"]["network"]["ssh"]
        self._host = ssh_config["host"]
        self._port = ssh_config.get("port", 22)
        self._username = ssh_config["username"]
        self._password = ssh_config["password"]
        self._timeout = ssh_config.get("timeout", 30.0)  # 30s default timeout
        self._command_timeout = ssh_config.get("command_timeout", 5.0)  # 5s default command timeout
        self._retry = ssh_config.get("retry", {
            "max_attempts": 3,
            "delay": 5.0
        })
        
        # Initialize client
        self._client: Optional[paramiko.SSHClient] = None
        self._terminal = None
        
        # Command queue and lock
        self._command_queue: asyncio.Queue = asyncio.Queue(maxsize=self.MAX_QUEUE_SIZE)
        self._command_lock = asyncio.Lock()
        
        logger.info(f"Initialized SSH client for {self._host}")

    async def connect(self) -> None:
        """Connect to device over SSH."""
        attempt = 0
        while True:
            try:
                # Create SSH client
                self._client = paramiko.SSHClient()
                self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                # Connect and get shell
                self._client.connect(
                    self._host,
                    port=self._port,
                    username=self._username,
                    password=self._password,
                    timeout=self._timeout
                )
                
                # Set up terminal
                self._client.get_transport().window_size = 2 * 1024 * 1024
                self._terminal = self._client.invoke_shell(term="vt100")
                
                # Initialize gpascii
                time.sleep(0.2)
                response = await self._read_response()
                await self._send_raw("gpascii -2\r\n")
                time.sleep(1.0)
                
                response = await self._read_response()
                logger.debug(f"gpascii response: {response}")
                
                # Handle error case where we need to retry
                if "Err" in response:
                    logger.warning("gpascii error, retrying after delay")
                    time.sleep(18)
                    await self._send_raw("gpascii -2\r\n")
                    time.sleep(1)
                    response = await self._read_response()
                    logger.debug(f"gpascii retry response: {response}")
                
                # Test echo
                if not ("Err" in response):
                    await self._send_raw("echo1\n\r")
                    response = await self._read_response(size=256)
                    logger.debug(f"echo response: {response}")
                
                self._connected = True
                logger.info(f"Connected to SSH at {self._host}")
                break
            
            except Exception as e:
                attempt += 1
                if attempt >= self._retry["max_attempts"]:
                    logger.error(f"Failed to connect to SSH at {self._host} after {attempt} attempts: {str(e)}")
                    raise
                    
                logger.warning(f"Connection attempt {attempt} failed, retrying in {self._retry['delay']}s")
                time.sleep(self._retry["delay"])

    async def disconnect(self) -> None:
        """Disconnect from SSH."""
        if self._client:
            self._client.close()
            self._client = None
            self._terminal = None
        self._connected = False
        logger.info(f"Disconnected from SSH at {self._host}")

    async def _read_response(self, size: int = BUFFER_SIZE) -> str:
        """Read response from terminal with proper buffer handling.
        
        Args:
            size: Buffer size to read
            
        Returns:
            Response string
        """
        if not self._terminal:
            raise ConnectionError("SSH not connected")
            
        # Read in chunks until we get a complete response
        chunks = []
        while self._terminal.recv_ready():
            chunk = self._terminal.recv(size)
            if not chunk:
                break
            chunks.append(chunk)
            
        # Combine and decode
        response = b"".join(chunks).decode("utf8")
        return response

    async def _send_raw(self, data: str) -> None:
        """Send raw data to terminal.
        
        Args:
            data: Data to send
        """
        if not self._terminal:
            raise ConnectionError("SSH not connected")
            
        self._terminal.send(data)

    async def _send_command(self, command: str) -> List[str]:
        """Send command and get response with queueing.
        
        Args:
            command: Command to send
            
        Returns:
            List of response lines
        """
        # Add to queue
        try:
            await self._command_queue.put(command)
        except asyncio.QueueFull:
            raise RuntimeError(f"Command queue full ({self._command_queue.qsize()} commands)")
            
        # Wait for lock
        async with self._command_lock:
            try:
                # Get command from queue
                command = await self._command_queue.get()
                
                # Send command
                await self._send_raw(command)
                await asyncio.sleep(self._command_timeout)
                
                # Get and parse response
                response = await self._read_response()
                response = response.split("\r\n")
                response = [msg for msg in response if msg != ""]
                
                logger.debug(f"Command '{command}' response: {response}")
                return response
                
            except Exception as e:
                logger.error(f"Failed to send command '{command}' to {self._host}: {str(e)}")
                raise
            finally:
                self._command_queue.task_done()

    async def read_tag(self, tag: str) -> Any:
        """Read tag value.
        
        Args:
            tag: Tag name to read
            
        Returns:
            Tag value
        """
        if not self._connected:
            raise ConnectionError("SSH not connected")
            
        # Send read command (e.g. P12)
        response = await self._send_command(f"{tag}\n")
        
        # Parse response
        if not response:
            raise ValueError(f"No response reading tag '{tag}' from {self._host}")
            
        try:
            # Response format is "P12=1"
            value = response[0].split("=")[1].strip()
            return int(value)  # Convert to int
            
        except Exception as e:
            logger.error(f"Failed to parse response for tag '{tag}' from {self._host}: {response} ({str(e)})")
            raise

    async def write_tag(self, tag: str, value: Any) -> None:
        """Write tag value.
        
        Args:
            tag: Tag name to write
            value: Value to write
        """
        if not self._connected:
            raise ConnectionError("SSH not connected")
            
        # Send write command (e.g. P12=1)
        try:
            response = await self._send_command(f"{tag}={value}\n")
            
            # Check response
            if not response or "Error" in str(response):
                raise RuntimeError(f"Error writing tag '{tag}' = {value} to {self._host}: {response}")
                
            logger.debug(f"Wrote tag {tag} = {value}")
            
        except Exception as e:
            logger.error(f"Failed to write tag '{tag}' = {value} to {self._host}: {str(e)}")
            raise

    def is_connected(self) -> bool:
        """Check if client is connected.
        
        Returns:
            Connection status
        """
        return self._connected
