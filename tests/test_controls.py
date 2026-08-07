import unittest

import pygame

from game.controls import Controls


class ControlsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controls = Controls()

    def send(self, event_type: int, key: int) -> None:
        self.controls.handle_event(pygame.event.Event(event_type, key=key))

    def test_short_direction_tap_survives_keyup_in_same_frame(self) -> None:
        self.send(pygame.KEYDOWN, pygame.K_RIGHT)
        self.send(pygame.KEYUP, pygame.K_RIGHT)
        self.assertEqual(self.controls.movement_axis(), (1, 0))
        self.assertEqual(self.controls.movement_axis(), (0, 0))

    def test_short_fire_tap_survives_keyup_in_same_frame(self) -> None:
        self.send(pygame.KEYDOWN, pygame.K_f)
        self.send(pygame.KEYUP, pygame.K_f)
        self.assertTrue(self.controls.wants_fire())
        self.controls.consume_fire()
        self.assertFalse(self.controls.wants_fire())

    def test_short_fire_tap_is_buffered_briefly(self) -> None:
        self.send(pygame.KEYDOWN, pygame.K_f)
        self.send(pygame.KEYUP, pygame.K_f)
        self.controls.update(0.1)
        self.assertTrue(self.controls.wants_fire())
        self.controls.update(0.06)
        self.assertFalse(self.controls.wants_fire())

    def test_held_key_remains_active(self) -> None:
        self.send(pygame.KEYDOWN, pygame.K_LEFT)
        self.assertEqual(self.controls.movement_axis(), (-1, 0))
        self.assertEqual(self.controls.movement_axis(), (-1, 0))
        self.send(pygame.KEYUP, pygame.K_LEFT)
        self.assertEqual(self.controls.movement_axis(), (0, 0))

    def test_focus_loss_clears_all_input(self) -> None:
        self.send(pygame.KEYDOWN, pygame.K_DOWN)
        self.controls.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertEqual(self.controls.movement_axis(), (0, 0))


if __name__ == "__main__":
    unittest.main()
