import sys
from pathlib import Path
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'ci'))
from weekly_publisher_wait import FIRST_WINDOW, INTERVAL, LAST_WINDOW, newest_main_run, wait_for_publisher


class WeeklyWaitTests(unittest.TestCase):
    def simulate(self, slots, statuses, start=60000, resumed=None):
        current = [start if resumed is None else resumed]
        observations = []
        statuses = iter(statuses)

        def latest():
            observations.append((current[0] - start) / INTERVAL)
            status = next(statuses)
            return None if status is None else {'id': 42, 'status': status}

        def sleep(seconds):
            current[0] += seconds

        result = wait_for_publisher(start, slots, latest, clock=lambda: current[0], sleep=sleep, log=lambda _: None)
        return result, observations

    def test_tries_now_and_at_30_minute_intervals_until_done(self):
        self.assertEqual(self.simulate(FIRST_WINDOW, ['queued', 'in_progress', 'completed']), (True, [0, 1, 2]))

    def test_no_run_does_not_skip_receipt_binding(self):
        self.assertEqual(self.simulate(FIRST_WINDOW, [None]), (True, [0]))

    def test_wait_budget_across_the_two_runner_jobs(self):
        self.assertEqual(self.simulate(FIRST_WINDOW, ['in_progress'] * 11), (False, list(range(11))))
        self.assertEqual(self.simulate(LAST_WINDOW, ['in_progress', 'in_progress'], resumed=60060 + 10 * INTERVAL), (False, [11, 12]))
        self.assertEqual(self.simulate(LAST_WINDOW, ['in_progress', 'completed'], resumed=60060 + 10 * INTERVAL), (True, [11, 12]))

    def test_does_not_use_newer_pr_or_off_main_run(self):
        base = {'head_branch': 'main', 'event': 'workflow_run', 'created_at': '2026-11-24T00:01:00Z', 'id': 20}
        pr = dict(base, event='pull_request', created_at='2026-11-24T00:30:00Z', id=22)
        branch = dict(base, head_branch='test', event='workflow_dispatch', id=21)
        earlier = dict(base, created_at='2026-11-24T00:00:00Z', id=1)
        self.assertEqual(newest_main_run([pr, earlier, branch, base]), base)

    def test_unknown_status_is_a_failure(self):
        with self.assertRaises(RuntimeError):
            self.simulate(FIRST_WINDOW, ['unexpected'])


if __name__ == '__main__':
    unittest.main()
