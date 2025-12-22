"""
Balance lock/unlock handlers for MainWindow.
"""

import logging
import tkinter as tk
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class BalanceHandlersMixin:
    """Mixin providing balance lock/unlock functionality for MainWindow."""

    def _toggle_balance_lock(self: "MainWindow"):
        """Handle lock/unlock button press."""
        from ui.balance_edit_dialog import BalanceRelockDialog, BalanceUnlockDialog

        if self.balance_locked:
            BalanceUnlockDialog(
                parent=self.root,
                current_balance=self.state.get("balance"),
                on_confirm=self._unlock_balance,
            )
        else:
            BalanceRelockDialog(
                parent=self.root,
                manual_balance=self.state.get("balance"),
                tracked_balance=self.tracked_balance,
                on_choice=self._relock_balance,
            )

    def _unlock_balance(self: "MainWindow"):
        """Allow manual balance editing."""
        self.balance_locked = False
        self.balance_lock_button.config(text="\U0001f513")  # 🔓
        self._start_balance_edit()

    def _relock_balance(self: "MainWindow", choice: str, new_balance: Decimal | None = None):
        """Re-lock balance, applying user's chosen balance."""
        if choice == "custom" and new_balance is not None:
            current = self.state.get("balance")
            delta = new_balance - current
            if delta != Decimal("0"):
                self.state.update_balance(delta, f"Manual balance set to {new_balance:.4f} SOL")

            self.state.set_baseline_balance(
                new_balance, reason=f"User set balance to {new_balance:.4f} SOL"
            )

            self.tracked_balance = new_balance
            logger.info(f"Balance baseline set to {new_balance:.4f} SOL (P&L tracking reset)")

        elif choice == "revert_to_pnl":
            delta = self.tracked_balance - self.state.get("balance")
            if delta != Decimal("0"):
                self.state.update_balance(delta, "Relock to P&L balance")

        self.balance_locked = True
        self.manual_balance = None
        self.balance_lock_button.config(text="\U0001f512")  # 🔒
        self.balance_label.config(text=f"WALLET: {self.state.get('balance'):.4f} SOL")

    def _start_balance_edit(self: "MainWindow"):
        """Replace balance label with inline editor."""
        from ui.balance_edit_dialog import BalanceEditEntry

        self.balance_label.pack_forget()
        self.balance_edit_entry = BalanceEditEntry(
            parent=self.balance_label.master,
            current_balance=self.state.get("balance"),
            on_save=self._apply_manual_balance,
            on_cancel=self._cancel_balance_edit,
        )
        self.balance_edit_entry.pack(side=tk.RIGHT, padx=4)

    def _apply_manual_balance(self: "MainWindow", new_balance: Decimal):
        """Apply user-entered manual balance and keep unlocked."""
        current = self.state.get("balance")
        delta = new_balance - current
        if delta != 0:
            self.state.update_balance(delta, "Manual balance override")
        self.manual_balance = new_balance
        self.balance_edit_entry.destroy()
        self.balance_label.config(text=f"WALLET: {new_balance:.4f} SOL")
        self.balance_label.pack(side=tk.RIGHT, padx=4)

    def _cancel_balance_edit(self: "MainWindow"):
        """Cancel manual edit and restore label."""
        if hasattr(self, "balance_edit_entry"):
            self.balance_edit_entry.destroy()
        self.balance_label.pack(side=tk.RIGHT, padx=4)

    def _handle_balance_changed(self: "MainWindow", data):
        """Handle balance change (thread-safe via TkDispatcher)"""
        new_balance = data.get("new")
        if new_balance is not None:
            self.tracked_balance = new_balance

            if self.server_authenticated:
                logger.debug(
                    f"Skipping local balance UI update (server authenticated): {new_balance}"
                )
                return

            if self.balance_locked:
                self.ui_dispatcher.submit(
                    lambda: self.balance_label.config(text=f"WALLET: {new_balance:.4f} SOL")
                )
