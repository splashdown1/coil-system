import csv
import datetime
from typing import Optional, List

class TruControlCenter:
    """
    COIL-integrated trade control center.
    Handles circuit breakers, trade evidence, and session auditing
    for the Tru_Moonshot_Sniper strategy.
    """

    def __init__(
        self,
        daily_drawdown_limit: float = 0.15,
        starting_balance: float = 10.0,
        cooldown_minutes: int = 60,
        manual_approval_threshold: float = 1.0
    ):
        self.daily_limit      = daily_drawdown_limit
        self.starting_balance = starting_balance
        self.current_balance  = starting_balance
        self.cooldown_minutes = cooldown_minutes
        self.manual_approval_threshold = manual_approval_threshold
        self.is_active        = True
        self.cooldown_until  : Optional[datetime.datetime] = None
        self.win_streak      = 0
        self.session_trades   = 0
        self.log_file        = 'tru_session_log.csv'

    # ── Circuit Breaker ────────────────────────────────────────────────────

    def update_circuit_breaker(self, current_balance: float) -> bool:
        """Halt bot if daily drawdown exceeds threshold."""
        self.current_balance = current_balance
        loss = self.starting_balance - current_balance
        pct  = loss / self.starting_balance

        if pct >= self.daily_limit:
            self.is_active = False
            self._log({
                'event': 'CIRCUIT_BREAKER_TRIGGERED',
                'drawdown_pct': f"{pct*100:.2f}%",
                'balance': current_balance
            })
            print(f"🔴 CIRCUIT BREAKER: {pct*100:.2f}% loss — bot halted.")
            return False

        # Auto-scale cap check
        if self.win_streak > 0:
            max_bet = min(0.1 * (1.2 ** self.win_streak), 0.5)
            print(f"   Streak {self.win_streak} | next max bet: {max_bet:.3f} SOL")
        return True

    def in_cooldown(self) -> bool:
        if self.cooldown_until is None:
            return False
        if datetime.datetime.now() < self.cooldown_until:
            return True
        self.cooldown_until = None
        return False

    def trigger_cooldown(self):
        self.cooldown_until = datetime.datetime.now() + datetime.timedelta(
            minutes=self.cooldown_minutes
        )
        self._log({'event': 'COOLDOWN_STARTED', 'minutes': self.cooldown_minutes})

    def requires_manual_approval(self, bet_size: float) -> bool:
        return bet_size >= self.manual_approval_threshold

    # ── Trade Evidence ─────────────────────────────────────────────────────

    def log_trade(self, data: dict):
        """Append trade row to CSV evidence log."""
        data['timestamp'] = datetime.datetime.now().isoformat()
        data['win_streak'] = self.win_streak
        data['is_active']  = self.is_active

        file_exists = False
        try:
            with open(self.log_file, 'r') as f:
                file_exists = True
        except FileNotFoundError:
            pass

        fieldnames = [
            'timestamp', 'token_address', 'action', 'price',
            'pulse_score', 'rug_check_passed', 'pnl_pct',
            'win_streak', 'is_active', 'event', 'minutes'
        ]
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(data)

        self.session_trades += 1

    def on_win(self):
        self.win_streak += 1
        self._log({'event': 'WIN', 'win_streak': self.win_streak})

    def on_loss(self):
        self.win_streak = 0
        self.trigger_cooldown()
        self._log({'event': 'LOSS', 'streak_reset': True})

    # ── Session Report ────────────────────────────────────────────────────

    def print_session_summary(self):
        elapsed = (datetime.datetime.now() - datetime.datetime.now()).total_seconds()
        net = self.current_balance - self.starting_balance
        roi = (net / self.starting_balance) * 100
        print(f"\n{'='*50}")
        print(f"  TRU SESSION SUMMARY")
        print(f"{'='*50}")
        print(f"  Starting balance : {self.starting_balance:.4f} SOL")
        print(f"  Current balance  : {self.current_balance:.4f} SOL")
        print(f"  Net P&L          : {'+' if net >= 0 else ''}{net:.4f} SOL ({roi:+.2f}%)")
        print(f"  Total trades     : {self.session_trades}")
        print(f"  Max win streak    : {self.win_streak}")
        print(f"  Bot active        : {self.is_active}")
        print(f"  Cooldown          : {self.in_cooldown()}")
        print(f"{'='*50}\n")

    def _log(self, data: dict):
        data['timestamp'] = datetime.datetime.now().isoformat()
        data['win_streak'] = self.win_streak
        data['is_active']  = self.is_active
        data['event']      = data.get('event', 'INFO')

        fieldnames = [
            'timestamp', 'token_address', 'action', 'price',
            'pulse_score', 'rug_check_passed', 'pnl_pct',
            'win_streak', 'is_active', 'event', 'minutes'
        ]
        try:
            with open(self.log_file, 'r') as f:
                pass
            file_exists = True
        except FileNotFoundError:
            file_exists = False
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(data)


# ── Example usage ─────────────────────────────────────────────────────────
if __name__ == '__main__':
    control = TruControlCenter(
        daily_drawdown_limit=0.15,
        starting_balance=10.0,
        cooldown_minutes=60,
        manual_approval_threshold=1.0
    )

    # Simulate trade cycle
    new_balance = 10.3
    if control.update_circuit_breaker(new_balance):
        print("✅ Bot active — processing snipes")

    control.log_trade({
        'token_address': 'Example123...',
        'action': 'BUY',
        'price': 0.00234,
        'pulse_score': 7200,
        'rug_check_passed': True,
        'pnl_pct': 0.0
    })

    control.on_win()
    control.print_session_summary()