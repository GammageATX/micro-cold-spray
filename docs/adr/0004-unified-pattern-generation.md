# Unified Point-Based Pattern Generation

## Status
Proposed

## Context
The system needs to generate various spray patterns (serpentine, spiral, custom, etc.) for cold spray operations. Previously, we used different file formats and generators for each pattern type, leading to:
- Multiple file formats to maintain
- Separate execution paths
- Complex validation rules
- Redundant code
- Harder to add new patterns

## Decision
We will implement a unified point-based pattern generation system where all patterns, regardless of type, are ultimately converted to and stored as point lists. This approach will be part of the Process API.

### Pattern Generation Flow
```
Pattern Request (with parameters)
         ↓
Pattern-Specific Generator
         ↓
Common Point Format
         ↓
Validation & Optimization
         ↓
Point File Storage
```

### Core Components

1. Point Format:
   ```python
   @dataclass
   class Point:
       x: float
       y: float
       z: float
       feed_rate: float
       dwell_time: Optional[float] = None
       metadata: Dict[str, Any] = field(default_factory=dict)
   ```

2. Pattern Generator Interface:
   ```python
   class PatternGenerator(ABC):
       @abstractmethod
       async def generate_points(
           self, 
           params: Dict[str, Any]
       ) -> List[Point]:
           """Generate point list from pattern parameters."""
           pass

       @abstractmethod
       async def validate_parameters(
           self, 
           params: Dict[str, Any]
       ) -> bool:
           """Validate pattern parameters."""
           pass
   ```

3. Pattern Types:
   ```python
   class SerpentineGenerator(PatternGenerator):
       async def generate_points(self, params):
           # Convert serpentine parameters to points
           # - Start position
           # - Line length
           # - Line spacing
           # - Number of passes
           return points

   class SpiralGenerator(PatternGenerator):
       async def generate_points(self, params):
           # Convert spiral parameters to points
           # - Center position
           # - Start radius
           # - End radius
           # - Spacing
           return points

   class CustomGenerator(PatternGenerator):
       async def generate_points(self, params):
           # Direct point list input
           # - Validate point format
           # - Check constraints
           return points
   ```

4. File Format:
   ```json
   {
     "metadata": {
       "pattern_type": "serpentine",
       "created_at": "ISO timestamp",
       "version": "1.0"
     },
     "parameters": {
       "specific": "pattern parameters"
     },
     "points": [
       {
         "x": 0.0,
         "y": 0.0,
         "z": 0.0,
         "feed_rate": 100.0,
         "dwell_time": 0.0
       }
     ]
   }
   ```

### API Endpoints

1. Pattern Generation:
   ```
   POST /api/process/patterns/generate
   {
     "type": "serpentine",
     "parameters": {
       "start_x": 0.0,
       "start_y": 0.0,
       "length": 100.0,
       "spacing": 5.0,
       "passes": 10
     }
   }
   ```

2. Pattern Validation:
   ```
   POST /api/process/patterns/validate
   {
     "points": [...],
     "constraints": {
       "max_feed_rate": 1000,
       "min_spacing": 1.0,
       "work_envelope": {...}
     }
   }
   ```

3. Pattern Operations:
   ```
   GET    /api/process/patterns/{id}
   PUT    /api/process/patterns/{id}
   DELETE /api/process/patterns/{id}
   GET    /api/process/patterns/types
   ```

## Consequences

### Positive
1. Single file format to maintain
2. Unified validation system
3. Simpler motion control interface
4. Easier to add new pattern types
5. Better testability
6. Consistent error handling
7. Simplified data persistence
8. Clear API interface

### Negative
1. Need to migrate existing pattern files
2. More complex generators for some patterns
3. Potentially larger file sizes
4. Need to handle point optimization

## Implementation Plan

1. Phase 1 - Core Infrastructure:
   - Point data structures
   - Base generator interface
   - File format handling
   - Basic validation

2. Phase 2 - Pattern Generators:
   - Serpentine pattern
   - Spiral pattern
   - Custom point input
   - Parameter validation

3. Phase 3 - Optimization:
   - Point reduction
   - Path optimization
   - Performance tuning
   - Advanced validation

4. Phase 4 - Migration:
   - Convert existing patterns
   - Update clients
   - Add backwards compatibility

## References
- Original pattern generators
- Motion control requirements
- Process API design
- Cold spray process constraints 