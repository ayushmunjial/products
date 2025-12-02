# Impact Parameters Investigation Report

## Answers to Loren's Questions

### 1. Are we pulling from the EC3 API or their openEPD API?

**Answer: We are pulling from the EC3 API.**

- **Primary API**: `https://buildingtransparency.org/api/epds` (EC3 API)
- **Secondary API**: `https://openepd.buildingtransparency.org/api/epds` (openEPD API) - Available but not currently used
- **Current Status**: All 184,614 EPDs were pulled from EC3 API

### 2. Do we need to combine data from both APIs?

**Answer: Currently, no - but infrastructure is ready.**

**Findings:**
- Both APIs return empty `impacts: {}` and `resource_uses: {}` fields
- EC3 API has complete GWP/carbon emissions data (96.2% coverage)
- openEPD API structure is different and also has empty impact/resource fields
- **Infrastructure Ready**: We've built merge utilities (`merge_impact_data.py`) that can combine data from both APIs when it becomes available

**Recommendation**: Monitor both APIs. If openEPD starts providing impact/resource data, we can enable `ENABLE_OPENEPD_FETCH = True` to automatically merge it.

### 3. Where are the impact categories and resource indicators?

## Current Status: Impact Categories & Resource Indicators

### Carbon Emissions (GWP) ✅ COMPLETE
- **Status**: Present in 96.2% of EPDs
- **Fields Found**:
  - `gwp`: Main Global Warming Potential
  - `best_practice`: Best practice estimate
  - `conservative_estimate`: Conservative estimate
  - `lowest_plausible_gwp`: Lowest plausible value
  - `uncertainty_adjusted_gwp`: Uncertainty-adjusted value
  - Category percentiles: `pct10_gwp` through `pct90_gwp`
  - Plant-level: `plant_or_group.carbon_intensity`

### Other LCIA Impact Categories ⚠️ EMPTY
- **Status**: Fields exist but are empty
- **Expected Fields**: `impacts` object should contain:
  - Ozone depletion potential
  - Acidification potential
  - Eutrophication potential
  - Photochemical ozone creation / smog formation
  - Abiotic resource depletion

**Analysis Results:**
- Scanned 184,614 EPDs across all regions
- **0 EPDs** have populated `impacts` field
- All EPDs show: `impacts: {}` (empty dictionary)
- PCR (Product Category Rules) show `lcia_requirements` but `impacts: []` arrays are empty

**Example Structure Found:**
```yaml
pcr:
  lcia_requirements:
    CML 2016:
      impacts: []  # Empty array
    TRACI 2.1:
      impacts: []  # Empty array
```

### Resource Use & Waste Indicators ⚠️ EMPTY
- **Status**: Fields exist but are empty
- **Expected Fields**: `resource_uses` object should contain:
  - Primary energy use (renewable / non-renewable)
  - Water use indicators
  - Waste generation and output flows

**Analysis Results:**
- Scanned 184,614 EPDs across all regions
- **0 EPDs** have populated `resource_uses` field
- All EPDs show: `resource_uses: {}` (empty dictionary)

## Data Structure

The EPD structure supports these fields:

```yaml
# Impact categories (currently empty)
impacts: {}

# Resource use indicators (currently empty)
resource_uses: {}

# Carbon emissions (populated)
gwp: 53.38 kgCO2e
best_practice: 44.02100617 kgCO2e
conservative_estimate: 62.73899383 kgCO2e
# ... and many more GWP fields
```

## What We've Built

1. **Analysis Scripts**: `analyze_emissions_data.py` - Scans all EPDs to find impact/resource data
2. **API Testing**: `test_openepd_api.py` - Tests openEPD API access and structure
3. **API Comparison**: `compare_apis.py` - Compares EC3 vs openEPD APIs
4. **Merge Infrastructure**: `merge_impact_data.py` - Ready to combine data from both APIs
5. **Main Script Updated**: `product-footprints.py` - Can fetch from openEPD when enabled

## Recommendations

1. **Current State**: Impact/resource data is not available in either API at this time
2. **Monitoring**: Continue monitoring both APIs for when this data becomes available
3. **When Available**: Enable `ENABLE_OPENEPD_FETCH = True` to automatically merge additional data
4. **Alternative**: Check if impact data is available through:
   - Direct EPD document downloads (PDF attachments)
   - Different API endpoints
   - Manual data entry from EPD documents

## Summary

- ✅ **GWP/Carbon Emissions**: Complete and available (96.2% coverage)
- ⚠️ **Other LCIA Categories**: Fields exist but empty in both APIs
- ⚠️ **Resource Indicators**: Fields exist but empty in both APIs
- ✅ **Infrastructure**: Ready to merge data when it becomes available

