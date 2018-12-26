Assuming you're in the directory where you cloned this Git repository (i.e. one level up from here), try:

```bash
curl -o weather/sunny.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=1338
curl -o weather/sunny-with-clouds.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=8756
curl -o weather/cloud-partly.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=2286
curl -o weather/cloudy.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=12019
curl -o weather/fog.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=17056
curl -o weather/moon-stars.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=16310
curl -o weather/rain-snow.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=160
curl -o weather/rain.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=72
curl -o weather/snow-house.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=7075
curl -o weather/snowy.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=2289
curl -o weather/thunderstorm.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=11428
# Convert JSON to a less verbose binary representation
scripts/convert-animation.py weather/*.json
rm weather/*.json
```
