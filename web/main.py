import asyncio

from game.config import FPS
from game.game import Game
from game.web import WebInputBridge


async def main() -> None:
    game = Game()
    bridge = WebInputBridge()
    game.start()
    while game.running:
        suspended = bridge.pump()
        dt = min(game.clock.tick(FPS) / 1000.0, 1 / 30)
        game.run_frame(dt, active=not suspended)
        bridge.sync_state(game.state)
        await asyncio.sleep(0)


asyncio.run(main())
