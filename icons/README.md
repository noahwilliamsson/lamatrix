Assuming you're in the directory where you cloned this Git repository (i.e. one level up from here), try:

```bash
curl -o icons/game-brick.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=1524
curl -o icons/game-invaders-1.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=3405
curl -o icons/game-invaders-2.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=3407
curl -o icons/game-tetris.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=4007
curl -o icons/game-nintendo.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=5038
curl -o icons/game-pacman-ghosts.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=20117
curl -o icons/game-pingpong.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=4075
curl -o icons/game-snake.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=16036
curl -o icons/matrix.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=653
curl -o icons/newyears.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=9356
curl -o icons/tv-movie.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=7862
# Convert JSON to a less verbose binary representation
scripts/convert-animation.py icons/*.json
rm icons/*.json
```

You might want to update `AnimationScene.filenames` in [config.json](../config.json) to make use of the animations.
