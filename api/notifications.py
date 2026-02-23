"""
ReconX Notification Manager
Sends alerts via Discord, Telegram, and Slack webhooks
"""

import logging
from typing import Optional, Dict
from datetime import datetime

import aiohttp

logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self):
        self.discord_webhook: Optional[str] = None
        self.telegram_bot_token: Optional[str] = None
        self.telegram_chat_id: Optional[str] = None
        self.slack_webhook: Optional[str] = None
        self._load_config()
    
    def _load_config(self):
        """Load notification configuration from config file"""
        try:
            import json
            with open('config/settings.json', 'r') as f:
                config = json.load(f)
                notifications = config.get('notifications', {})
                self.discord_webhook = notifications.get('discord_webhook')
                self.telegram_bot_token = notifications.get('telegram_bot_token')
                self.telegram_chat_id = notifications.get('telegram_chat_id')
                self.slack_webhook = notifications.get('slack_webhook')
        except Exception:
            pass
    
    async def send_notification(self, title: str, message: str, 
                                 severity: str = "info",
                                 fields: Optional[Dict] = None):
        """Send notification to all configured channels"""
        tasks = []
        
        if self.discord_webhook:
            tasks.append(self._send_discord(title, message, severity, fields))
        
        if self.telegram_bot_token and self.telegram_chat_id:
            tasks.append(self._send_telegram(title, message, fields))
        
        if self.slack_webhook:
            tasks.append(self._send_slack(title, message, severity, fields))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_discord(self, title: str, message: str, 
                           severity: str, fields: Optional[Dict]):
        """Send Discord webhook"""
        color_map = {
            "critical": 0xFF0000,
            "high": 0xFF6600,
            "medium": 0xFFCC00,
            "low": 0x00CCFF,
            "info": 0x00FF00
        }
        
        embed = {
            "title": title,
            "description": message,
            "color": color_map.get(severity, 0x00FF00),
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {"text": "ReconX"}
        }
        
        if fields:
            embed["fields"] = [
                {"name": k, "value": str(v), "inline": True}
                for k, v in fields.items()
            ]
        
        payload = {"embeds": [embed]}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.discord_webhook,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status not in [200, 204]:
                        logger.warning(f"Discord notification failed: {resp.status}")
        except Exception as e:
            logger.error(f"Discord notification error: {e}")
    
    async def _send_telegram(self, title: str, message: str, 
                            fields: Optional[Dict]):
        """Send Telegram message"""
        text = f"*{title}*\n\n{message}"
        
        if fields:
            text += "\n\n" + "\n".join([f"*{k}*: {v}" for k, v in fields.items()])
        
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        
        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"Telegram notification failed: {resp.status}")
        except Exception as e:
            logger.error(f"Telegram notification error: {e}")
    
    async def _send_slack(self, title: str, message: str,
                         severity: str, fields: Optional[Dict]):
        """Send Slack webhook"""
        color_map = {
            "critical": "#FF0000",
            "high": "#FF6600",
            "medium": "#FFCC00",
            "low": "#00CCFF",
            "info": "#00FF00"
        }
        
        attachment = {
            "color": color_map.get(severity, "#00FF00"),
            "title": title,
            "text": message,
            "footer": "ReconX",
            "ts": int(datetime.utcnow().timestamp())
        }
        
        if fields:
            attachment["fields"] = [
                {"title": k, "value": str(v), "short": True}
                for k, v in fields.items()
            ]
        
        payload = {"attachments": [attachment]}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.slack_webhook,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"Slack notification failed: {resp.status}")
        except Exception as e:
            logger.error(f"Slack notification error: {e}")
    
    async def notify_scan_complete(self, scan_id: str, target: str, 
                                   findings: Dict):
        """Notify scan completion"""
        await self.send_notification(
            title="✅ Scan Completed",
            message=f"Scan for {target} has completed successfully.",
            severity="info",
            fields={
                "Scan ID": scan_id,
                "Critical": findings.get('critical', 0),
                "High": findings.get('high', 0),
                "Medium": findings.get('medium', 0),
                "Low": findings.get('low', 0)
            }
        )
    
    async def notify_critical_finding(self, scan_id: str, vuln_title: str,
                                      severity: str, url: str):
        """Notify critical vulnerability found"""
        await self.send_notification(
            title=f"🚨 Critical Finding: {vuln_title}",
            message=f"A {severity.upper()} severity vulnerability was detected.",
            severity=severity,
            fields={
                "Scan ID": scan_id,
                "URL": url,
                "Time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            }
        )
    
    async def notify_power_restored(self, tunnel_url: str, scan_status: Dict):
        """Notify when power/internet restored and scan resumed"""
        await self.send_notification(
            title="🔌 Power Restored - Scan Resumed",
            message=f"System back online. Scan resumed from {scan_status.get('progress', 'unknown')}%",
            severity="info",
            fields={
                "Dashboard": tunnel_url,
                "Status": scan_status.get('status', 'unknown'),
                "Paused For": scan_status.get('paused_duration', 'unknown')
            }
        )
    
    async def notify_tunnel_started(self, service: str, url: str):
        """Notify when tunnel starts"""
        await self.send_notification(
            title="🌐 Remote Access Enabled",
            message=f"{service.capitalize()} tunnel is now active.",
            severity="info",
            fields={
                "Service": service.capitalize(),
                "URL": url,
                "Local": "http://localhost:8000"
            }
        )
