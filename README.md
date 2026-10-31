# GreenMove Edge POC

Proof of concept for GreenMove Logistics demonstrating offline ZFE geofencing and telematics-based harsh braking detection on constrained edge hardware.

The project contains two main modules:

- **Geo Engine**: detects whether simulated GPS positions enter the Lyon ZFE using a Bounding Box optimization followed by a Ray Casting Point-in-Polygon algorithm.
- **Safety Engine**: analyzes longitudinal accelerometer data and detects harsh braking events using a lightweight threshold-based filter and streaming processing.

The POC is designed to run locally without any network dependency.

## Requirements

- Python 3.10 or later
- pip
- Git

The project was developed and tested with:

- Python 3.14.4
- pytest 9.1.1

No external library is required by the application itself. `pytest` is only used for automated tests.

## Installation

Clone the repository:

```bash
git clone https://github.com/MyriamKuhn/greenmove-edge-poc.git
cd greenmove-edge-poc
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows with Git Bash:

```bash
source .venv/Scripts/activate
```

On Windows Command Prompt:

```cmd
.venv\Scripts\activate
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

Install the test dependency:

```bash
python -m pip install -r requirements.txt
```

## Project Structure

```text
greenmove-edge-poc/
├── data/
│   ├── accelerometer_data.csv
│   ├── lyon_polygon.json
│   └── truck_gps.json
├── scripts/
│   └── generate_demo_data.py
├── src/
│   ├── geo/
│   │   ├── __init__.py
│   │   ├── geo_engine.py
│   │   └── run_geo.py
│   └── safety/
│       ├── __init__.py
│       ├── safety_engine.py
│       └── run_safety.py
├── tests/
│   ├── geo/
│   │   └── test_geo_engine.py
│   └── safety/
│       └── test_safety_engine.py
├── run_demo.py
├── .gitignore
├── requirements.txt
└── README.md
```

## Run the Complete Demo

Run the complete POC with:

```bash
python run_demo.py
```

This executes the Geo Engine followed by the Safety Engine using the original datasets provided for the exercise.

Example output:

```text
=== GREENMOVE EDGE POC ===

=== GEO ENGINE ===
[GPS OUT] id=1 time=08:00:00
[GPS OUT] id=2 time=08:00:10
[GPS OUT] id=3 time=08:00:20
[ALERT ZFE] id=4 time=08:00:30 lat=45.76 lon=4.8357
[GPS IN] id=5 time=08:00:40

=== SAFETY ENGINE ===
[HARSH BRAKING] timestamp=1678880005 acc_y=-3.45 m/s²
[SAFETY SUMMARY] samples=10 harsh_braking_events=1
[OUTPUT] daily_score.json

=== DEMO COMPLETE ===
```

For a higher-volume Edge Computing demonstration:

```bash
python run_demo.py --stress
```

The stress mode generates and processes 1000 accelerometer samples representing 10 seconds of data at a simulated 100 Hz sampling rate.

Only significant events are retained in the generated safety report.

Example:

```text
Generated 1000 samples in data\demo_accelerometer_1000.csv
[DEMO] Processing 1000 samples at simulated 100 Hz
[HARSH BRAKING] timestamp=1678881005.49 acc_y=-3.45 m/s²
[SAFETY SUMMARY] samples=1000 harsh_braking_events=1
[OUTPUT] daily_score.json
```

## Run the Geo Engine

From the project root:

```bash
python -m src.geo.run_geo
```

Example output:

```text
[GPS OUT] id=1 time=08:00:00
[GPS OUT] id=2 time=08:00:10
[GPS OUT] id=3 time=08:00:20
[ALERT ZFE] id=4 time=08:00:30 lat=45.76 lon=4.8357
[GPS IN] id=5 time=08:00:40
```

The Geo Engine works entirely from locally stored JSON files and does not require a network connection.

## Run the Safety Engine

From the project root:

```bash
python -m src.safety.run_safety
```

Example output:

```text
[HARSH BRAKING] timestamp=1678880005 acc_y=-3.45 m/s²
[SAFETY SUMMARY] samples=10 harsh_braking_events=1
[OUTPUT] daily_score.json
```

The command generates a `daily_score.json` file in the project root.

Example:

```json
{
  "total_samples": 10,
  "harsh_braking_events": 1,
  "events": [
    {
      "timestamp": 1678880005,
      "acc_y": -3.45
    }
  ]
}
```

## Run the Tests

Run all automated tests with:

```bash
python -m pytest -v
```

The current test suite contains 20 tests covering both the Geo and Safety engines.

## Input Files

The POC uses three local input files stored in the `data/` directory.

### `lyon_polygon.json`

Defines the simplified Lyon ZFE polygon as latitude/longitude coordinates.

The first and last coordinates are identical in order to explicitly close the polygon.

### `truck_gps.json`

Contains a simulated truck GPS trace.

Each entry includes:

- an identifier;
- a timestamp;
- latitude;
- longitude;
- an `expected` field supplied by the exercise dataset.

The Geo Engine uses the coordinates themselves for the geometric calculation.

### `accelerometer_data.csv`

Contains accelerometer samples with the following columns:

```text
timestamp,acc_x,acc_y,acc_z
```

The longitudinal axis used for braking detection is `acc_y`.

A strong negative Y acceleration represents vehicle deceleration.

## Geo Algorithm

### Bounding Box Optimization

Before executing the Point-in-Polygon calculation, the Geo Engine computes the polygon bounding box:

```text
min_lat
max_lat
min_lon
max_lon
```

For each GPS position, the engine first checks whether the point is inside this rectangle.

If the point is outside the bounding box, it cannot be inside the ZFE polygon and is immediately rejected.

This avoids running the more detailed Ray Casting calculation for obviously distant points.

The Bounding Box is calculated once and reused for all GPS positions.

### Ray Casting / Point in Polygon

For points that pass the Bounding Box check, the engine uses the Ray Casting algorithm.

Conceptually, a horizontal ray is projected from the GPS point toward one side of the plane.

The algorithm counts how many polygon edges intersect this ray:

- an odd number of intersections means the point is inside the polygon;
- an even number of intersections means the point is outside the polygon.

The implementation also explicitly checks whether a point lies directly on a polygon segment.

Boundary points are considered inside the ZFE.

The algorithm processes each polygon edge once, resulting in linear complexity relative to the number of polygon vertices:

```text
O(N)
```

This is appropriate for constrained edge hardware.

### ZFE Entry Detection

The Geo Engine also keeps track of the previous vehicle state.

The ZFE alert is triggered only when the vehicle transitions from outside to inside the polygon:

```text
OUT -> OUT  : no alert
OUT -> IN   : [ALERT ZFE]
IN  -> IN   : no repeated alert
IN  -> OUT  : vehicle leaves the zone
```

This avoids repeatedly alerting the driver while the vehicle remains inside the ZFE.

## Safety Algorithm

The Safety Engine focuses on the longitudinal Y axis.

The exercise dataset is expressed in `m/s²`.

A harsh braking event is detected when:

```text
acc_y < -2.5
```

For example:

```text
-0.80 m/s²  -> normal variation
-1.20 m/s²  -> normal variation
-3.45 m/s²  -> harsh braking
```

The threshold acts as a lightweight filtering mechanism.

Small variations and vehicle vibrations are ignored, while significant longitudinal deceleration is retained as an event.

A moving average was intentionally not used for this POC because smoothing a very short event could reduce its amplitude and hide the braking peak.

### Streaming Processing

Accelerometer samples are read one at a time using Python's standard CSV library.

The full dataset is not loaded into memory.

The engine only keeps:

- a sample counter;
- detected harsh braking events.

This reduces memory usage and is better suited to the constrained Zebra ET40 environment.

At 100 samples per second:

```text
1000 samples = 10 seconds of sensor data
```

The stress demonstration shows that the engine can process all 1000 samples while retaining only the significant braking event.

The processing complexity is linear:

```text
O(N)
```

## Output Files

### Geo Output

The Geo Engine writes its results to standard output.

When the vehicle enters the ZFE, the following log format is produced:

```text
[ALERT ZFE] id=4 time=08:00:30 lat=45.76 lon=4.8357
```

A vehicle that remains inside the zone is logged without repeating the alert:

```text
[GPS IN] id=5 time=08:00:40
```

Positions outside the zone are logged as:

```text
[GPS OUT] id=1 time=08:00:00
```

### Safety Output

The Safety Engine generates:

```text
daily_score.json
```

The generated file contains:

- the number of processed accelerometer samples;
- the number of detected harsh braking events;
- the timestamp and longitudinal acceleration of each event.

The output file is generated at runtime and is excluded from Git through `.gitignore`.

## Error Handling

The POC handles common input errors without displaying an uncontrolled traceback during normal execution.

Handled cases include:

- missing JSON input files;
- invalid JSON syntax;
- missing CSV input files;
- invalid numeric values in accelerometer data;
- missing or malformed required fields.

Example:

```text
[ERROR] File not found: data/truck_gps.json
```

or:

```text
[ERROR] File not found: data/accelerometer_data.csv
```

This behavior is important for the live demonstration because invalid input should be reported clearly without crashing the complete application flow.

## Dataset Note

The GPS dataset supplied with the exercise contains the following entry:

```json
{
  "id": 3,
  "timestamp": "08:00:20",
  "lat": 45.7850,
  "lon": 4.8050,
  "expected": "IN (Bordure)"
}
```

Using the polygon coordinates supplied in the same dataset, this point is geometrically outside the polygon according to the implemented Ray Casting calculation.

The implementation intentionally does not alter the algorithm to force the value of the `expected` field.

A separate automated test verifies that a point located exactly on a polygon boundary is correctly considered inside.

This keeps the geometric implementation deterministic while documenting the dataset inconsistency explicitly.

## Performance Considerations

The target Zebra ET40 environment has limited application memory and may receive up to 100 sensor points per second.

The POC therefore follows several lightweight design principles:

- no external geospatial framework;
- no pandas or NumPy dependency;
- Bounding Box rejection before Ray Casting;
- linear O(N) algorithms rather than nested O(N²) processing;
- local processing without network dependency;
- accelerometer streaming instead of loading the full dataset into memory;
- retention of detected events instead of the complete raw sensor history;
- compact JSON output for the daily safety report.

The stress mode demonstrates the processing of 1000 samples at a simulated 100 Hz sampling rate while retaining only the relevant harsh braking event.

This illustrates the Edge Computing principle used by the project: process raw data locally and keep only useful information for later storage or transmission.

## Limitations of the POC

This project is intentionally limited to the technical feasibility requested by the proof of concept.

Current limitations include:

- the ZFE polygon is a simplified static dataset;
- there is no production-grade European map database;
- there is no Android sensor integration;
- GPS data is simulated from a JSON file;
- accelerometer data is simulated from a CSV file;
- the harsh braking threshold is fixed;
- the daily report does not implement an insurer-specific scoring formula;
- detected events are still stored in memory until the daily JSON file is written;
- there is no local database yet;
- there is no deferred Cloud synchronization yet;
- there is no graphical driver interface.

These elements would belong to a production implementation rather than to the core feasibility POC.

## Design Rationale

The implementation deliberately favors simple, deterministic and explainable algorithms.

The Geo module validates that ZFE detection can operate without network access, directly addressing the failure mode of the previous Cloud-dependent application.

The Safety module validates that local accelerometer data can produce behavioral driving evidence by isolating significant braking events from normal variations.

The streaming approach reduces memory usage while the stress demonstration confirms that high-frequency input can be processed locally without retaining all raw measurements.

Both modules use lightweight local processing, making the POC suitable for demonstrating the Edge Computing approach on constrained hardware.