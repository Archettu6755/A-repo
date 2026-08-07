import unittest

import pygame

from game.controls import Controls, event_key


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

    def test_fire_scancode_works_with_unknown_keycode(self) -> None:
        self.controls.handle_event(
            pygame.event.Event(
                pygame.KEYDOWN,
                key=pygame.K_UNKNOWN,
                scancode=pygame.KSCAN_F,
            )
        )
        self.assertTrue(self.controls.wants_fire())

    def test_event_key_prefers_known_scancode(self) -> None:
        event = pygame.event.Event(
            pygame.KEYDOWN,
            key=pygame.K_e,
            scancode=pygame.KSCAN_F,
        )
        self.assertEqual(event_key(event), pygame.K_f)

    def test_event_key_falls_back_when_scancode_is_missing(self) -> None:
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e)
        self.assertEqual(event_key(event), pygame.K_e)

    def test_unicode_f_wins_over_conflicting_movement_identity(self) -> None:
        self.controls.handle_event(
            pygame.event.Event(
                pygame.KEYDOWN,
                key=pygame.K_LEFT,
                scancode=pygame.KSCAN_LEFT,
                unicode="f",
            )
        )
        self.assertTrue(self.controls.wants_fire())
        self.assertEqual(self.controls.movement_axis(), (0, 0))

    def test_fire_release_uses_its_press_scancode(self) -> None:
        self.controls.handle_event(
            pygame.event.Event(
                pygame.KEYDOWN,
                key=pygame.K_LEFT,
                scancode=pygame.KSCAN_LEFT,
                unicode="f",
            )
        )
        self.assertTrue(self.controls.wants_fire())
        self.controls.handle_event(
            pygame.event.Event(
                pygame.KEYUP,
                key=pygame.K_LEFT,
                scancode=pygame.KSCAN_LEFT,
            )
        )
        self.controls.consume_fire()
        self.assertFalse(self.controls.wants_fire())

    def test_focus_loss_clears_fire_state(self) -> None:
        self.send(pygame.KEYDOWN, pygame.K_f)
        self.controls.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertFalse(self.controls.wants_fire())

    def test_latest_direction_wins_when_opposite_key_is_stale(self) -> None:
        self.send(pygame.KEYDOWN, pygame.K_LEFT)
        self.send(pygame.KEYDOWN, pygame.K_RIGHT)
        self.assertEqual(self.controls.movement_axis(), (1, 0))
        self.send(pygame.KEYUP, pygame.K_RIGHT)
        self.assertEqual(self.controls.movement_axis(), (-1, 0))

        self.send(pygame.KEYDOWN, pygame.K_UP)
        self.send(pygame.KEYDOWN, pygame.K_DOWN)
        self.assertEqual(self.controls.movement_axis(), (-1, 1))
        self.send(pygame.KEYUP, pygame.K_DOWN)
        self.assertEqual(self.controls.movement_axis(), (-1, -1))


if __name__ == "__main__":
    unittest.main()
