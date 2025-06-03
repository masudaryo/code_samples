from __future__ import annotations
from winrt.windows.ui.notifications.management import UserNotificationListener
from winrt.windows.ui.notifications import UserNotificationChangedEventArgs
import asyncio
from asyncio import AbstractEventLoop
import sys

class NotificationProcessInvoker:
    def __init__(self, subprocess_filepath: str) -> None:
        self.subprocess_filepath = subprocess_filepath
        self.user_notification_listener = UserNotificationListener.current
        access_status = self.user_notification_listener.get_access_status()
        if access_status.name != "ALLOWED":
            raise Exception(f"UserNotificationListener access: {access_status.name}")
        self.loop: AbstractEventLoop
        self.notification_id_queue: asyncio.Queue[int] = asyncio.Queue()

    async def notification_process_loop(self) -> None:
        async with asyncio.TaskGroup() as tg:
            while True:
                notification_id = await self.notification_id_queue.get()
                asyncio_process = await asyncio.create_subprocess_exec("python", self.subprocess_filepath, str(notification_id))
                tg.create_task(asyncio_process.wait())

    def notification_changed_handler(self, sender: UserNotificationListener, args: UserNotificationChangedEventArgs) -> None:
        # クラッシュを回避するため、引数のオブジェクトをこのhandlerの外に持ち出さないように注意する。また、handler内でのcall_soon_threadsafe()は問題ないがrun_coroutine_threadsafe()はクラッシュするためevent loopにcoroutineを実行させることはできない。e.g. asyncio.Queue.put()はcoroutineなので使えないがasyncio.Queue.put_nowait()はcoroutineではないので使える
        if args.change_kind.name == "ADDED":
            self.loop.call_soon_threadsafe(self.notification_id_queue.put_nowait, int(args.user_notification_id))

    async def run(self) -> None:
        self.loop = asyncio.get_running_loop()
        event_token = self.user_notification_listener.add_notification_changed(self.notification_changed_handler)
        try:
            await self.notification_process_loop()
        finally:
            # https://github.com/pywinrt/pywinrt/blob/main/projection/readme.md#event-handlers
            self.user_notification_listener.remove_notification_changed(event_token)

def main() -> None:
    asyncio.run(NotificationProcessInvoker(sys.argv[1]).run())

if __name__ == "__main__":
    main()
