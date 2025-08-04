[Profile Tools](../profile) and [IO Template](../io/template)

# Product Comparisons

**BuildingTransparency.org API**
[IO Template: Nutrition-style Labels](/io/template/) - [Interactive Label Display](/profile/item/)  
[State .csv files pulled from BuildingTransparency API](https://github.com/ModelEarth/products/tree/main/US)  
[YAML-TO-JSON-TO-HTML parser](/io/template/parser/)  
[BuildingTransparency Feed View (Static EPD json)](/feed/view/#feed=epd)  
[Product Feed API](/io/template/feed) - [View product profiles in BuildingTransparency.org](https://buildingtransparency.org/ec3/epds/ec3mmgup)  
<!-- Environmental Product Declarations (EPD) -->

<!--[View as Markdown](/io/template/product/product-concrete.html)-->


 


TO CONTRIBUTE: [Fork](https://github.com/ModelEarth/MaterialScience) and run [MaterialScience](/MaterialScience) as a webroot on your computer.  
Add your first name after the project you are working on below, send a PR and email Loren to pull.

US/GA/GA.yaml was too big: 97.3 MB
Avoid pushing files larger then 25 MB.

TO DO: The token expires every 72 hours, so switch our ["Update Data" GitHub Action](https://github.com/ModelEarth/profile/actions) to use an email and password as the secrets which generate the token. (Look at how we use a myconfig file locally to get a new token and create a similar process in the GitHub Action.) Test in a fork and document steps for adding the secrets here. The URL for the API may need to be updated to https://buildingtransparency.org/api/epds

TO DO: product-footprints.py and update\_csv\_and\_yaml.py are very similar. Add "-DELETE" to the name of one (as long as we can use the other file two ways: locally and with the GitHub Action workflow). If retaining update_csv_and_yaml.py, change underscores to dashes.

TO DO: Send the cement product rows to their own files in new state folders in profile/cement/US. Save the cement listings within the same process that saves non-cement for states. (Avoid loading and process the CSV file containing all states.)

TO DO: Use Postman to test pulling CO2 for products. Update csv list output with product emission impacts for all states by updating our [Python Profile pull](https://github.com/ModelEarth/profile/tree/main/products/pull/)<!-- product-footprints.py -->. View [Resulting Data](https://github.com/ModelEarth/profile/tree/main/products/US).

TO DO: Save emissions info within our indvidual YAML files. Include all the impact (emmissions, etc) in each profile. Login to BuildingTransparency.org to view a [detail sample](https://buildingtransparency.org/ec3/epds/ec3mmgup).  Update our notes with your findings and progress. You can use Postman or another app to explore the BuildingTransparency APIs.

TO DO: Change from using UUIDs in the yaml file names. Instead, let's use product names to create SEO-friendly file paths. Retain the subfolders that are product categories.

TO DO: We can also experimenting with [pulling directly to json](pull/get-json/). (Might not work.)


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


