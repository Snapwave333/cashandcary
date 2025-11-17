"""
Alerting and notification system for the arbitrage bot.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from decimal import Decimal
from typing import Optional
import json

from .models import ArbitrageOpportunity, Trade
from .config import BotSettings


logger = logging.getLogger(__name__)


class AlertLevel:
    """Alert severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class Alert:
    """Represents an alert message."""

    def __init__(
        self,
        level: str,
        title: str,
        message: str,
        data: dict = None,
        timestamp: datetime = None
    ):
        self.level = level
        self.title = title
        self.message = message
        self.data = data or {}
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert alert to dictionary."""
        return {
            "level": self.level,
            "title": self.title,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }

    def __str__(self) -> str:
        return f"[{self.level}] {self.title}: {self.message}"


class AlertManager:
    """Manages alerting and notifications."""

    def __init__(self, settings: BotSettings):
        self.settings = settings
        self.alert_history: list[Alert] = []
        self._email_configured = self._check_email_config()

    def _check_email_config(self) -> bool:
        """Check if email alerting is properly configured."""
        # In production, check for SMTP settings
        return self.settings.alert_email is not None

    def send_alert(self, alert: Alert) -> bool:
        """
        Send an alert through configured channels.

        Args:
            alert: Alert to send

        Returns:
            True if alert was sent successfully
        """
        self.alert_history.append(alert)
        logger.log(
            self._get_log_level(alert.level),
            f"ALERT: {alert}"
        )

        # Write to alert log file
        self._write_to_file(alert)

        # Send email if configured
        if self._email_configured and self._should_email(alert):
            self._send_email_alert(alert)

        return True

    def _get_log_level(self, alert_level: str) -> int:
        """Convert alert level to logging level."""
        mapping = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.CRITICAL: logging.CRITICAL,
        }
        return mapping.get(alert_level, logging.INFO)

    def _should_email(self, alert: Alert) -> bool:
        """Determine if alert should trigger email."""
        # Always email critical alerts
        if alert.level == AlertLevel.CRITICAL:
            return True

        # Email opportunities if configured
        if "opportunity" in alert.title.lower() and self.settings.alert_on_opportunity:
            return True

        # Email trades if configured
        if "trade" in alert.title.lower() and self.settings.alert_on_trade:
            return True

        return False

    def _write_to_file(self, alert: Alert) -> None:
        """Write alert to file."""
        try:
            with open("alerts.log", "a") as f:
                f.write(json.dumps(alert.to_dict(), default=str) + "\n")
        except Exception as e:
            logger.error(f"Failed to write alert to file: {e}")

    def _send_email_alert(self, alert: Alert) -> None:
        """Send alert via email (placeholder implementation)."""
        if not self.settings.alert_email:
            return

        # In production, implement actual SMTP sending
        logger.info(f"Would send email to {self.settings.alert_email}: {alert.title}")

        # Placeholder for actual email implementation
        """
        msg = MIMEMultipart()
        msg['From'] = 'arbitrage-bot@example.com'
        msg['To'] = self.settings.alert_email
        msg['Subject'] = f"[{alert.level}] {alert.title}"

        body = f'''
        Alert: {alert.title}
        Level: {alert.level}
        Time: {alert.timestamp}

        {alert.message}

        Data: {json.dumps(alert.data, indent=2, default=str)}
        '''
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP('smtp.example.com', 587) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
        """

    def alert_opportunity_found(self, opportunity: ArbitrageOpportunity) -> None:
        """Send alert for a profitable opportunity."""
        alert = Alert(
            level=AlertLevel.INFO,
            title=f"Arbitrage Opportunity Found - {opportunity.symbol}",
            message=(
                f"Found profitable opportunity in {opportunity.symbol}:\n"
                f"Contract: {opportunity.futures_contract.contract_code}\n"
                f"Profit: {opportunity.profit_percentage:.4%}\n"
                f"Expected profit/contract: ${opportunity.expected_profit_per_contract}"
            ),
            data={
                "symbol": opportunity.symbol,
                "contract": opportunity.futures_contract.contract_code,
                "spot_price": float(opportunity.spot_price.price),
                "futures_price": float(opportunity.actual_futures_price),
                "theoretical_price": float(opportunity.theoretical_futures_price),
                "profit_percentage": float(opportunity.profit_percentage),
                "expected_profit": float(opportunity.expected_profit_per_contract),
            }
        )
        self.send_alert(alert)

    def alert_trade_executed(self, trade: Trade) -> None:
        """Send alert for executed trade."""
        alert = Alert(
            level=AlertLevel.INFO,
            title=f"Trade Executed - {trade.symbol}",
            message=(
                f"Successfully executed arbitrage trade:\n"
                f"Trade ID: {trade.trade_id}\n"
                f"Symbol: {trade.symbol}\n"
                f"Spot: {trade.spot_side} {trade.spot_quantity} @ ${trade.spot_price}\n"
                f"Futures: {trade.futures_side} {trade.futures_quantity} contracts @ ${trade.futures_price}\n"
                f"Expected Profit: ${trade.expected_profit}\n"
                f"Status: {trade.status}"
            ),
            data={
                "trade_id": trade.trade_id,
                "symbol": trade.symbol,
                "spot_quantity": float(trade.spot_quantity),
                "spot_price": float(trade.spot_price),
                "futures_quantity": trade.futures_quantity,
                "futures_price": float(trade.futures_price),
                "expected_profit": float(trade.expected_profit),
                "dry_run": trade.dry_run,
            }
        )
        self.send_alert(alert)

    def alert_error(self, error_message: str, exception: Exception = None) -> None:
        """Send alert for errors."""
        alert = Alert(
            level=AlertLevel.CRITICAL,
            title="Bot Error",
            message=error_message,
            data={
                "exception": str(exception) if exception else None,
                "exception_type": type(exception).__name__ if exception else None,
            }
        )
        self.send_alert(alert)

    def alert_risk_warning(self, warning_message: str, exposure: Decimal) -> None:
        """Send alert for risk-related warnings."""
        alert = Alert(
            level=AlertLevel.WARNING,
            title="Risk Warning",
            message=warning_message,
            data={
                "current_exposure": float(exposure),
                "max_exposure": float(self.settings.max_total_exposure),
            }
        )
        self.send_alert(alert)

    def get_alert_summary(self) -> dict:
        """Get summary of alerts."""
        levels = {AlertLevel.INFO: 0, AlertLevel.WARNING: 0, AlertLevel.CRITICAL: 0}
        for alert in self.alert_history:
            if alert.level in levels:
                levels[alert.level] += 1

        return {
            "total_alerts": len(self.alert_history),
            "by_level": levels,
            "recent_alerts": [a.to_dict() for a in self.alert_history[-10:]],
        }


def setup_logging(settings: BotSettings) -> None:
    """
    Configure logging for the bot.

    Args:
        settings: Bot settings with log configuration
    """
    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    simple_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level))

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler(settings.log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)

    # Separate file for errors
    error_handler = logging.FileHandler("errors.log")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)

    logger.info("Logging configured successfully")
