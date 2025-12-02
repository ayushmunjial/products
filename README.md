[Profile Tools](../profile) and [IO Template](../io/template)


TO DO: We're creating a cool UX for viewing and comparing [menus of product impacts](../profile/item/menu.html).  
Here's an upcoming [product profile](../profile/item/index.html#layout=product). (Change to use this [raw yaml path for Accostic Ceilings](https://raw.githubusercontent.com/ModelEarth/products-data/refs/heads/main/US/Acoustical_Ceilings/61a3d3f6469b4e9baa9da7605650a63d.yaml).)

[Getting Started](#start) as a code contributor

# Environmental Product Data

## YAML File Structure
The YAML details in the [products-data repo](https://github.com/modelearth/products-data/) contain CO2e impact data for building products pulled from BuildingTransparency.org. Each file represents a specific product's Environmental Product Declaration (EPD) with lifecycle assessment data.

**Most interesting:** the gwp_z parameter compares to category average.


### Global Warming Potential (GWP)
The primary emission metric tracked is carbon footprint, measured in kgCO2e:

### Category Identifiers
Each product belongs to a category with unique identifiers.
The category.id UUID is the most reliable. We organize by category.name for ease of use.

- **category.name**: Machine-readable name (e.g., "AcousticalCeilings")
- **category.display_name**: User-friendly display name (e.g., "Acoustical Ceilings")
- **category.openepd**: Hierarchical classification in OpenEPD system (e.g., "Finishes >> CeilingPanel >> AcousticalCeilings")
- **category.masterformat**: MasterFormat classification code (e.g., "09 51 00 Acoustical Ceilings")
- **category.unspsc**: United Nations Standard Products and Services Code
- **category.id**: Primary unique identifier (UUID format) - most reliable for referencing


#### Product-Specific Values
- **gwp**: Total GWP for the declared unit (e.g., 1000 sf, 1 m³)
- **gwp_per_category_declared_unit**: GWP normalized to the category's standard declared unit (typically 1 m²)
- **gwp_per_kg**: GWP per kilogram of product

#### Category Percentiles
Industry benchmarks showing the distribution of emissions across all products in the category:
- **pct10_gwp**: 10th percentile - lowest 10% of products
- **pct20_gwp**: 20th percentile
- **pct30_gwp**: 30th percentile
- **pct40_gwp**: 40th percentile
- **pct50_gwp**: 50th percentile (median value)
- **pct60_gwp**: 60th percentile
- **pct70_gwp**: 70th percentile
- **pct80_gwp**: 80th percentile
- **pct90_gwp**: 90th percentile - 90% of products fall below this level

### Statistical Values
- **best_practice**: Best-case emission scenario (lowest plausible GWP)
- **conservative_estimate**: Worst-case emission scenario (highest plausible GWP)
- **lowest_plausible_gwp**: Minimum feasible GWP value
- **uncertainty_adjusted_gwp**: GWP adjusted for data uncertainty
- **standard_deviation**: Measure of variability in the data
- **uncertainty_factor**: Multiplier used to adjust for data uncertainty
- **gwp_z**: Z-score showing how this product's GWP compares to category average

### Carbon Storage
- **biogenic_embodied_carbon_z**: Z-score for biogenic carbon content
- **stored_carbon_z**: Z-score for long-term carbon storage potential
- **use_stored_carbon**: Boolean indicating whether stored carbon is included in calculations

## Transportation Impacts

**Important:** EPD GWP values represent **A1-A3 stages only** (cradle-to-gate):
- **A1**: Raw material extraction and processing
- **A2**: Transportation of raw materials TO the manufacturing facility (included in gwp)
- **A3**: Manufacturing at the facility

**Transportation to the construction site (A4) is typically NOT included** in the reported `gwp` value because manufacturers don't know where products will be installed.

Category-level transportation assumptions:
- **category.default_distance**: Default transportation distance in kilometers for A4 stage (factory to construction site) - used in lifecycle assessment calculations when actual shipping distances are unknown
- **category.default_transport_mode**: Assumed method of transportation (e.g., "truck, unspecified")

### Adjusting for Actual Transportation Distance

To calculate the environmental impact when purchasing products at a different distance from the manufacturing location:

**Transportation Emission Formula:**
```
Transportation Impact (kgCO2e) = Distance (km) × Load (kg) × Emission Factor (kgCO2e/ton-km) ÷ 1000

Where:
- Distance = Actual distance from manufacturing to construction site (km)
- Load = mass_per_declared_unit (kg) - found in the product YAML
- Emission Factor (truck) ≈ 0.062 kgCO2e/ton-km (typical for diesel truck)
```

**Adjusted Total GWP:**
```
Adjusted GWP = gwp + (Actual Transportation Impact - Default Transportation Impact)

Where:
- Default Transportation Impact = category.default_distance × mass_per_declared_unit × 0.062 ÷ 1000
- Actual Transportation Impact = Your actual distance × mass_per_declared_unit × 0.062 ÷ 1000
```

**Example Calculation:**
```
Product gwp: 468 kgCO2e (for 1000 sf)
mass_per_declared_unit: 357.43 kg
category.default_distance: 1647.968 km

Default transport impact: 1647.968 × 357.43 × 0.062 ÷ 1000 = 36.5 kgCO2e
Actual distance: 500 km (purchased locally)
Actual transport impact: 500 × 357.43 × 0.062 ÷ 1000 = 11.1 kgCO2e

Adjusted GWP = 468 + (11.1 - 36.5) = 442.6 kgCO2e
Savings: 25.4 kgCO2e (5.4% reduction)
```

**Note on Supply Chain Transportation:**
The reported `gwp` value already includes transportation of raw materials and components to the manufacturing facility (A2 stage). The adjustment above only accounts for the final transportation from manufacturing to construction site (A4). Complex supply chains with extensive pre-manufacturing transportation are already reflected in the base `gwp` value.


## Missing Impact Categories

The following environmental impact metrics are frequently **not specified** in EPDs:
- **ODP**: Ozone Depletion Potential
- **AP**: Acidification Potential
- **EP-FRESH**: Freshwater Eutrophication Potential
- **EP-MARINE**: Marine Eutrophication Potential
- **EP-TERRESTRIAL**: Terrestrial Eutrophication Potential
- **POCP**: Photochemical Ozone Creation Potential

<div id="start"></div>

These missing fields indicate that many EPDs focus primarily on carbon emissions (GWP) rather than the full spectrum of environmental impacts.


## Product Comparisons

[See issue page on GitHub for additional details](https://github.com/ModelEarth/products/issues/1)

**BuildingTransparency.org API**  
1. [View product profiles in BuildingTransparency.org](https://buildingtransparency.org/ec3/epds/ec3mmgup)  
Click "OpenEPD json" in the upper right on a product page. Pull the same via the API and save in [country]/[category] folders.

2. Update detail file output with product emission impacts for all countries and states/territories by updating our [Python Profile pull](https://github.com/ModelEarth/products/tree/main/pull)<!-- product-footprints.py -->. (Postman may be helpful for exploring API data structure.)

3. Send resulting data to a fork of [ModelEarth/products-data](https://github.com/ModelEarth/products-data/) - View a recent pull in [Sirisha's fork](https://github.com/Sirishaupadhyayula/products-data).



**Our Product Menu Frontend**

4. Send produdt detail files to our [Interactive Label Display](/profile/item/)  

5. [IO Template: Nutrition-style Labels](/io/template/)  

6. Update [Product Feed API pull via Javascript](/io/template/feed)  

7. Add select menu to [YAML-TO-JSON-TO-HTML parser](/io/template/parser/)  

8. Fix images on the [BuildingTransparency Feed View (Static EPD json)](/team/projects/#list=epd) 

<!--
8. Update the [BuildingTransparency Feed View (Static EPD json)](/feed/view/#feed=epd)  
-->

<!-- Environmental Product Declarations (EPD) -->

<!--[View as Markdown](/io/template/product/product-concrete.html)-->



## Getting Started

TO CONTRIBUTE: Fork and run [webroot](https://github.com/ModelEarth/webroot) on your computer. Find an issue listed at [model.earth/projects](https://model.earth/projects) and post a reply to it with your work in progress and update your post when you send a PR with the update.

Avoid pushing files larger then 25 MB - breaks Cloudflare static hosting pull 
All details in one state file resulted in a 97.3 MB file for the state of Georgia.

<!-- probably done,  Sounds like Noor added to Python.
TO DO: The token expires every 72 hours, so switch our ["Update Data" GitHub Action](https://github.com/ModelEarth/profile/actions) to use an email and password as the secrets which generate the token. (Look at how we use a myconfig file locally to get a new token and create a similar process in the GitHub Action.) Test in a fork and document steps for adding the secrets here. The URL for the API may need to be updated to https://buildingtransparency.org/api/epds
-->

DONE: product-footprints.py and update\_csv\_and\_yaml.py are very similar. Add "-DELETE" to the name of one (as long as we can use the other file two ways: locally and with the GitHub Action workflow). If retaining update_csv_and_yaml.py, change underscores to dashes.

DONE: Send the cement product rows to their own files in new state folders in profile/cement/US. Save the cement listings within the same process that saves non-cement for states. (Avoid loading and process the CSV file containing all states.)

DONE: Save emissions info within our indvidual YAML files. Include all the impact (emmissions, etc) in each profile. Login to BuildingTransparency.org to view a [detail sample](https://buildingtransparency.org/ec3/epds/ec3mmgup).  See [EMISSIONS_DATA_DOCUMENTATION.md](pull/EMISSIONS_DATA_DOCUMENTATION.md) for details on impact categories and resource use data.

<!--
TO DO: We can also experimenting with [pulling directly to json](pull/get-json/). (Might not work.)
-->

## Fetch Product Data

1. Fork and clone the [Profile Repo](https://github.com/ModelEarth/profile) for 

2. In our products/pull folder myconfig.py file, you'll add a username and password.

3. Get your login (and token) from the [BuildingTransparency.org](https://BuildingTransparency.org) website

For products/pull/product-footprints.py set your BuildingTransparency email and password in [myconfig.py](https://github.com/ModelEarth/profile/tree/main/products/pull/) to call the API.


**Run in your Profile folder**  
We have not yet tested "pip install functools" below yet

    python3 -m venv env
    source env/bin/activate

For Windows

    python3 -m venv env
    .\env\Scripts\activate

Run the following in the root of the Profile repo. Takes over 30 minutes.

    pip install requests pandas pyyaml
    pip install functools
    python products/pull/product-footprints.py

<!-- Resolved by changing endpoint
Current Error: Max retries exceeded with url: /api/rest-auth/login (Caused by ConnectTimeoutError(<urllib3.connection.HTTPSConnection object at 0x104c69c70>, 'Connection to etl-api.cqd.io timed out. (connect timeout=None)'))
-->

<!--
June 3, 2024 - We copied [product-footprints.py](https://github.com/ModelEarth/profile/tree/main/products/pull/) into [Product Footprints Colab](https://colab.research.google.com/drive/1TJ1fn0-_8EBryN3ih5hZiKLISomOrWDW?usp=sharing) (We haven't run as CoLab yet.)
-->


## Get API Key for Product Profile YAML

The [Central Concrete EPD data](https://github.com/modelearth/io/blob/master/template/product/product-concrete.yaml) was pulled from the BuildingTransparency.org API using the following steps:  

**STEP 1:** Create an account at [buildingtransparency.org](https://www.buildingtransparency.org/)

**STEP 2:** Use your email and password to get your bearer "key" here in Swagger: [openepd.buildingtransparency.org](https://openepd.buildingtransparency.org) - Click Authorize.

NOTE: Your BuildingTransparency API Key will expire after 3 days. Our python process automatically refreshes the key using your settings added to products/pull/myconfig.py.

**STEP 3:** Open a command terminal, and get the "Bearer" secret key entering YOUR EMAIL as the username and YOUR PASSWORD.

    curl -X POST -d "{\"username\":\"YOUR EMAIL\",\"password\":\"YOUR PASSWORD\"}" "https://etl-api.cqd.io/api/rest-auth/login" -H "accept: application/json" -H "Content-Type: application/json"


**RETURNS**

~~~
{"key":"xxxxxxxxxxxxxxxxxxxxxxxx","last_login":"2021-08-12T02:49:09.850397Z"}%   
~~~

Which you'll append as:

~~~
-H "Authorization: Bearer xxxxxxxxxxxxxxxxxxxxxxxx"
~~~

// https://buildingtransparency.org/ec3/manage-apps/api-doc/guide#/01_Overview/01_Introduction.md

Click "Create API Key"
https://buildingtransparency.org/ec3/manage-apps/keys

**Example:**

~~~
curl -X 'GET' \
 'https://openepd.buildingtransparency.org/api/epds?page_number=1&page_size=100' \
 -H 'accept: application/json' \
 -H 'filter: {"epds.name":"ASTM International"}' \
 -H 'Authorization: Bearer xxxxxxxxxxxxxxxxxxxxxxxx'
~~~

**Tip:** Use the [EC3 frontend](https://buildingtransparency.org/ec3/material-search) of the tool and watch the commands it issues in the dev inspector's network tab. 

Georgia Mass Timber:

https://buildingtransparency.org/api/materials?page_number=1&page_size=25&soft_search_terms=true&category=b03dba1dca5b49acb1a5aa4daab546b4&jurisdiction=US-FL&epd__date_validity_ends__gt=2021-08-24


~~~
curl -X 'GET' \
  'https://openepd.buildingtransparency.org/api/epds?page_number=1&page_size=1' \
  -H 'accept: application/json' \
  -H "Authorization: Bearer xxxxxxxxxxxxxxxxxxxxxxxx"
~~~

<div id="postman"></div>

To convert to yaml, the json can be pasted in either: [json2yaml.com](https://www.json2yaml.com/) or [editor.swagger.io](https://editor.swagger.io)

<br>

# View API in Postman

0. Create a "Workspace" in Postman
1. Click on "Import" tab on the upper left side.
2. Paste your cURL command (which is Raw Text).
3. Hit import and you will have the command in your Postman builder!
4. Click Send to post the command.

[How to use Curl with Postman](https://www.google.com/search?q=how+to+use+Curl+with+Postman&oq=how+to+use+Curl+with+Postman&aqs=chrome..69i57.18359j0j9&sourceid=chrome&ie=UTF-8) - [YouTube](https://www.google.com/search?q=how+to+use+Curl+with+Postman&sxsrf=APq-WBtPCQSW52ZIvoJZxIvspDVdEJ_G0g:1648670885549&source=lnms&tbm=vid&sa=X&ved=2ahUKEwio-u_T0e72AhXWmGoFHSTLB6sQ_AUoAXoECAEQAw&biw=1513&bih=819&dpr=1)
<br>

# Get YAML for IO Template

[For IO Template](../) - Use OpenEPD swagger

<!-- https://etl-api.cqd.io/ No longer works -->

BuildingTransparency OpenEPD API
[https://openepd.buildingtransparency.org/#/epds/get_epds_id](openepd.buildingtransparency.org/#/epds/get_epds_id)


Inside Postman, you can load the swagger.yaml file [exported from Swagger](https://stackoverflow.com/questions/48525546/how-to-export-swagger-json-or-yaml) which will import the schemas into Postman.

## Impact Categories & Resource Use Data

### Carbon Emissions (GWP)

All EPD YAML files contain comprehensive carbon emissions data:
- **Primary GWP fields**: `gwp`, `gwp_per_kg`, `best_practice`, `conservative_estimate`, etc.
- **Category percentiles**: `category.pct10_gwp` through `category.pct90_gwp`
- **Plant-level data**: `plant_or_group.carbon_intensity`

### Other LCIA Impact Categories

The following impact categories may be available in the `impacts` field (currently empty in EC3 API responses):
- Ozone depletion potential
- Acidification potential
- Eutrophication potential
- Photochemical ozone creation / smog formation
- Abiotic resource depletion

### Resource Use Indicators

The following resource indicators may be available in the `resource_uses` field (currently empty in EC3 API responses):
- Primary energy use (renewable / non-renewable)
- Water use indicators
- Waste generation and output flows

### API Usage

- **Primary API**: EC3 API (`https://buildingtransparency.org/api/epds`) - Used for all EPD data
- **Secondary API**: openEPD API (`https://openepd.buildingtransparency.org/api/epds`) - Optional, can be used to supplement impact/resource data

To enable openEPD API fetching for additional impact/resource data, set `ENABLE_OPENEPD_FETCH = True` in `product-footprints.py`.

### Analysis & Testing Scripts

Several scripts are available in `products/pull/` to analyze and test impact data:

- **`analyze_emissions_data.py`**: Scans existing YAML files to document emissions fields and coverage
- **`test_openepd_api.py`**: Tests openEPD API access and inspects response structure
- **`compare_apis.py`**: Compares EC3 and openEPD APIs side-by-side
- **`test_impact_data_integration.py`**: Tests merge functionality and YAML structure

For detailed documentation, see [EMISSIONS_DATA_DOCUMENTATION.md](pull/EMISSIONS_DATA_DOCUMENTATION.md).
