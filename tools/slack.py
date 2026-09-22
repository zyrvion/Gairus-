class SlackTool:
    def send(self, channel, text):
        return {
            "channel": channel,
            "text": text,
            "status": "adapter_ready",
        }
