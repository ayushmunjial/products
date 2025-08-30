[Product Comparisons](../../)
# JSON Pull Attempt

The following is a copy of script used in the [useeio.js](https://github.com/modelearth/useeio.js) repo to download the full API to json files.

The get-json-bt.js page will need to be edited since it initially contains the useeio.js API structure.

Note that the Building Transparency API key expires every 3 days. [Get a BuildingTransparency.org key](https://model.earth/profile/products/).

```
$ node get-json-bt.js --apikey [Add API key here] --endpoint https://openepd.buildingtransparency.org/api/epds?page_number=1&page_size=10
```
