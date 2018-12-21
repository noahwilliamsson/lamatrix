Assuming you're in the directory where you cloned this Git repository (i.e. one level up from here), try:

```bash
curl -o animations/game-brick.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=1524
curl -o animations/game-invaders-1.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=3405
curl -o animations/game-invaders-2.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=3407
curl -o animations/game-nintendo.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=5038
curl -o animations/game-pacman-ghosts.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=20117
curl -o animations/game-pingpong.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=4075
curl -o animations/game-snake.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=16036
curl -o animations/matrix.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=653
curl -o animations/newyears.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=9356
curl -o animations/tv-movie.json https://developer.lametric.com/api/v1/dev/preloadicons?icon_id=7862
```

You might want to update `AnimationScene.filenames` in [config.json](../config.json) to make use of the animations.
