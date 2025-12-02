# Carbon Emissions & Impact Parameters Documentation

## Overview

This document describes where carbon emissions and other environmental impact parameters reside in the BuildingTransparency EPD data, and how we extract and integrate this information.

## Current API Usage

### Primary API: EC3 API
- **Endpoint**: `https://buildingtransparency.org/api/epds`
- **Authentication**: Bearer token from `https://buildingtransparency.org/api/rest-auth/login`
- **Current Status**: We are pulling all EPD data from EC3 API

### Secondary API: openEPD API (Optional)
- **Endpoint**: `https://openepd.buildingtransparency.org/api/epds`
- **Authentication**: Same Bearer token as EC3 API
- **Status**: Available for fetching additional impact/resource data when EC3 data is incomplete
- **Configuration**: Controlled by `ENABLE_OPENEPD_FETCH` flag in `product-footprints.py`

## Carbon Emissions Data Location

### Primary GWP Fields (Root Level)

All EPD YAML files contain the following carbon emissions fields at the root level:

- **`gwp`**: Main Global Warming Potential value (e.g., "53.38 kgCO2e")
- **`gwp_per_kg`**: GWP per kilogram
- **`gwp_per_category_declared_unit`**: GWP per declared unit
- **`best_practice`**: Best practice GWP estimate
- **`conservative_estimate`**: Conservative GWP estimate
- **`lowest_plausible_gwp`**: Lowest plausible GWP value
- **`uncertainty_adjusted_gwp`**: Uncertainty-adjusted GWP
- **`standard_deviation`**: Standard deviation of GWP
- **`gwp_z`**: GWP z-score
- **`biogenic_embodied_carbon_z`**: Biogenic carbon z-score
- **`stored_carbon_z`**: Stored carbon z-score

### Category Percentile Values

Within the `category` object, percentile GWP values are available:

- **`category.pct10_gwp`** through **`category.pct90_gwp`**: Percentile GWP values for the category

### Plant-Level Data

- **`plant_or_group.carbon_intensity`**: Plant electricity carbon intensity (e.g., "527.564 lbCO2e / MWh")

## Other LCIA Impact Categories

### Current Status

Based on analysis of existing EPD files, the `impacts` field is currently **empty** (`impacts: {}`) in all EC3 API responses. This means we need to check the openEPD API for additional impact categories.

### Expected LCIA Categories (from Loren's requirements)

When available, the following impact categories should be present in the `impacts` field:

1. **Ozone Depletion Potential** (`ozone_depletion`, `ozone_depletion_potential`, `odp`)
2. **Acidification Potential** (`acidification`, `acidification_potential`, `ap`)
3. **Eutrophication Potential** (`eutrophication`, `eutrophication_potential`, `ep`)
4. **Photochemical Ozone Creation / Smog Formation** (`photochemical_ozone`, `photochemical_ozone_creation`, `pocp`, `smog`)
5. **Abiotic Resource Depletion** (`abiotic_resource`, `abiotic_resource_depletion`, `ard`)

### Data Structure

```yaml
impacts:
  ozone_depletion_potential: <value>
  acidification_potential: <value>
  eutrophication_potential: <value>
  photochemical_ozone_creation: <value>
  abiotic_resource_depletion: <value>
```

## Resource Use & Waste Indicators

### Current Status

Based on analysis of existing EPD files, the `resource_uses` field is currently **empty** (`resource_uses: {}`) in all EC3 API responses. This means we need to check the openEPD API for resource use data.

### Expected Resource Indicators (from Loren's requirements)

When available, the following resource indicators should be present in the `resource_uses` field:

1. **Primary Energy Use (Renewable)** (`primary_energy_renewable`, `energy_renewable`)
2. **Primary Energy Use (Non-Renewable)** (`primary_energy_non_renewable`, `energy_non_renewable`)
3. **Water Use Indicators** (`water_use`, `water`, `water_consumption`)
4. **Waste Generation** (`waste_generation`, `waste`, `waste_output`)
5. **Output Flows** (`output_flows`, `output`)

### Data Structure

```yaml
resource_uses:
  primary_energy_renewable: <value>
  primary_energy_non_renewable: <value>
  water_use: <value>
  waste_generation: <value>
  output_flows: <value>
```

## API Comparison Results

### EC3 API
- **Strengths**: Complete GWP/carbon emissions data, all EPDs available
- **Weaknesses**: `impacts` and `resource_uses` fields are empty
- **Coverage**: 100% of EPDs have GWP data

### openEPD API
- **Status**: Needs testing to determine coverage
- **Potential**: May contain additional impact categories and resource use data
- **Usage**: Can be used to supplement EC3 data when `impacts` or `resource_uses` are empty

## Integration Approach

### Merge Strategy

We use a merge strategy that:

1. **Primary Source**: EC3 API provides the base EPD data
2. **Supplemental Source**: openEPD API provides additional impact/resource data when EC3 fields are empty
3. **Matching**: EPDs are matched between APIs using:
   - `id` field
   - `material_id` field
   - `open_xpd_uuid` field
4. **Merging**: Impact and resource data from openEPD is merged into EC3 data, with EC3 data taking precedence

### Implementation

The merge functionality is implemented in:
- **`merge_impact_data.py`**: Contains merge utility functions
- **`product-footprints.py`**: Main script with optional openEPD fetching

### Configuration

To enable openEPD API fetching, set in `product-footprints.py`:

```python
ENABLE_OPENEPD_FETCH = True  # Set to True to enable
```

**Note**: Enabling this will slow down processing as it requires additional API calls.

## Data Extraction Functions

### LCIA Category Extraction

The `extract_lcia_categories()` function in `merge_impact_data.py` extracts standardized LCIA categories from EPD data, mapping various field name variations to standard names.

### Resource Indicator Extraction

The `extract_resource_indicators()` function in `merge_impact_data.py` extracts standardized resource indicators from EPD data, mapping various field name variations to standard names.

## Analysis Scripts

### 1. `analyze_emissions_data.py`

Scans existing YAML files to document:
- All GWP/carbon fields present
- Impact categories found (if any)
- Resource use indicators found (if any)
- Coverage by country and category

**Usage**:
```bash
python3 analyze_emissions_data.py
```

### 2. `test_openepd_api.py`

Tests openEPD API access and inspects response structure:
- Tests authentication
- Fetches sample EPDs
- Checks for impact/resource data
- Saves sample response for inspection

**Usage**:
```bash
python3 test_openepd_api.py
```

### 3. `compare_apis.py`

Compares EC3 and openEPD APIs side-by-side:
- Fetches same EPD from both APIs
- Compares `impacts` and `resource_uses` fields
- Documents which API has more complete data
- Provides recommendations

**Usage**:
```bash
python3 compare_apis.py
```

### 4. `test_impact_data_integration.py`

Tests the integration functionality:
- Tests merge functions
- Verifies YAML structure preservation
- Validates field extraction

**Usage**:
```bash
python3 test_impact_data_integration.py
```

## File Structure

```
products/pull/
├── product-footprints.py          # Main script (updated with openEPD support)
├── merge_impact_data.py          # Merge utility functions
├── analyze_emissions_data.py      # Analysis script
├── test_openepd_api.py            # openEPD API testing
├── compare_apis.py                # API comparison script
├── test_impact_data_integration.py # Integration tests
└── EMISSIONS_DATA_DOCUMENTATION.md # This file
```

## Next Steps

1. **Run Analysis**: Execute `analyze_emissions_data.py` to document current data state
2. **Test openEPD API**: Run `test_openepd_api.py` to check if openEPD has additional data
3. **Compare APIs**: Run `compare_apis.py` to determine which API has more complete data
4. **Enable Integration**: If openEPD has additional data, set `ENABLE_OPENEPD_FETCH = True` in `product-footprints.py`
5. **Re-run Data Pull**: Re-run `product-footprints.py` to generate updated YAML files with merged data

## References

- BuildingTransparency.org API Documentation: https://buildingtransparency.org/ec3/manage-apps/api-doc/guide
- Perplexity Search: https://www.perplexity.ai/search/buildingtransparency-org-has-m-uYhBVU_zTB65nN5Nf7MpFw#0
- EC3 API: `https://buildingtransparency.org/api/epds`
- openEPD API: `https://openepd.buildingtransparency.org/api/epds`

## Summary

- **Carbon Emissions**: ✅ Already present in all EPD files (GWP fields)
- **Other LCIA Categories**: ⚠️ Currently empty in EC3 API, need to check openEPD API
- **Resource Use Indicators**: ⚠️ Currently empty in EC3 API, need to check openEPD API
- **Integration**: ✅ Implemented and ready to use when openEPD data is available

