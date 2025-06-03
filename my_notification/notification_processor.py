from __future__ import annotations
from winrt.windows.ui.notifications.management import UserNotificationListener
from winrt.windows.ui.notifications import ToastNotificationManager, ToastNotification, ToastTemplateType, UserNotification, Notification, NotificationBinding
from winrt.windows.applicationmodel import AppDisplayInfo, AppInfo
from winrt.windows.data.xml.dom import XmlElement
from collections.abc import Callable, Sequence, Generator, Iterable
import typing
from typing import Self, Any, Literal, Protocol, Never, assert_never
from abc import ABC, abstractmethod
import dataclasses
from os import PathLike
import json
import re
import datetime
import zoneinfo
import sys
import filelock
import channel_name_dicts


notificatoin_data_json_filepath: PathLike | str = r"notification_data.json"

edge_user_model_id: str = "Microsoft.MicrosoftEdge.Stable_8wekyb3d8bbwe!App"
discord_user_model_id: str = "com.squirrel.Discord.Discord"

edge_youtube_notification_history_id: str = "Microsoft.MicrosoftEdge.Stable_8wekyb3d8bbwe!https://www.youtube.com/"
edge_x_notification_history_id: str = "Microsoft.MicrosoftEdge.Stable_8wekyb3d8bbwe!https://x.com/"
edge_gmail_notification_history_id: str = "Microsoft.MicrosoftEdge.Stable_8wekyb3d8bbwe!https://mail.google.com/"

type YTContentType = Literal["is_live", "live_in_30_minutes", "members_only_is_live", "members_only_live_in_30_minutes", "premiere", "premiere_in_30_minutes", "video_upload", "got_a_gift_membership", "youtube_error"]

class YTPropertyExtractor:
    content_type_to_regexs: dict[YTContentType, tuple[re.Pattern, re.Pattern]] = {
        "is_live": (re.compile(r"🔴 (?P<title>.*)"),
                    re.compile(r"(?P<channel>.*) is live")),
        "live_in_30_minutes": (re.compile(r"YouTube"),
                               re.compile(r"Watch (?P<channel>.*) live in 30 minutes: (?P<title>.*)")),
        "members_only_is_live": (re.compile(r"🔴 Members-only live stream"),
                                 re.compile(r"(?P<channel>.*) is live: (?P<title>.*)")),
        "members_only_live_in_30_minutes": (re.compile(r"🔴 Members-only live stream"),
                                            re.compile(r"(?P<channel>.*) is live in 30 minutes: (?P<title>.*)")),
        "premiere": (re.compile(r"🔴 (?P<channel>.*): Premiere"),
                     re.compile(r"(?P<title>.*)")),
        "premiere_in_30_minutes": (re.compile(r"🔴 (?P<channel>.*): Premiere in 30 minutes"),
                                   re.compile(r"(?P<title>.*)")),
        "got_a_gift_membership": (re.compile("🎁 You got a gift membership!"),
                                  re.compile("Enjoy 1-month access to (?P<channel>.*) perks starting now")),
    }

    @classmethod
    def extract_properties(cls, text_elements: Sequence[str]) -> tuple[str, str, YTContentType] | None:
        """Youtubeの通知と判定できるとき、channel, title, YTContentType を返す。そうでないときNoneを返す。"""
        def match_lines(patterns: tuple[re.Pattern, re.Pattern], lines: Sequence[str]) -> tuple[str, str] | None:
            matchs = [pattern.fullmatch(line) for pattern, line in zip(patterns, lines)]
            if all(matchs):
                matchs = typing.cast(list[re.Match], matchs)
                channel = next((channel for m in matchs if (channel := m.groupdict().get("channel")) is not None), "")
                title = next((title for m in matchs if (title := m.groupdict().get("title")) is not None), "")
                return channel, title
            else:
                return None

        for content_type, regexs in cls.content_type_to_regexs.items():
            if (channel_title := match_lines(regexs, text_elements)) is not None:
                return *channel_title, content_type
        if text_elements[0] in channel_name_dicts.yt_all_channels:
            return text_elements[0], text_elements[1], "video_upload"
        elif text_elements[0] == "www.youtube.com" and text_elements[1] == "This site was updated in the background.":
            return "", "", "youtube_error"
        else:
            return None

@dataclasses.dataclass
class YouTubeNotification:
    channel_name: str
    title: str
    content_type: YTContentType
    user_notification_data: UserNotificationData

    @classmethod
    def from_user_notification_data(cls, user_notification_data: UserNotificationData) -> Self | Literal["youtube_error"] | None:
        if user_notification_data.get_app_user_model_id() != edge_user_model_id:
            return None
        elif (properties := YTPropertyExtractor.extract_properties(user_notification_data.get_text_elements())) is not None:
            if properties[2] == "youtube_error":
                return "youtube_error"
            if properties[0] not in channel_name_dicts.yt_all_channels:
                print_notify(f"Unknown YouTube channel name: {properties[0]} in {user_notification_data.get_text_elements()}")
            return cls(*properties, user_notification_data)
        else:
            return None

@dataclasses.dataclass
class TwitchGmailNotification:
    channel_name: str
    go_live_comment: str
    user_notification_data: UserNotificationData

    @classmethod
    def from_user_notification_data(cls, user_notification_data: UserNotificationData) -> Self | None:
        if user_notification_data.get_app_user_model_id() != edge_user_model_id:
            return None
        elif user_notification_data.get_text_elements()[0] == "Twitch":
            regex = re.compile(r"(?P<channel_name>.*) (?:is live|just went live on Twitch): (?P<go_live_comment>.*)")
            if m := regex.fullmatch(user_notification_data.get_text_elements()[1]):
                if m["channel_name"] not in channel_name_dicts.tw_all_channels:
                    print_notify(f"Unknown Twitch channel name: {m["channel_name"]} in {user_notification_data.get_text_elements()[1]}")
                return cls(m["channel_name"], m["go_live_comment"], user_notification_data)
            else:
                raise_notify(f"Twitch gmail notificaion {user_notification_data.get_text_elements()} has unknown pattern.")
        else:
            return None

@dataclasses.dataclass
class UserNotificationData:
    app_info: AppInfoData
    creation_time: tuple[str, float]
    id: int
    notification: NotificationData

    @classmethod
    def from_user_notification(cls, user_notification: UserNotification) -> Self:
        return  cls(
            try_default(lambda: AppInfoData.from_app_info(user_notification.app_info)),
            try_default(lambda: process_datetime(user_notification.creation_time)),
            try_default(lambda: user_notification.id),
            try_default(lambda: NotificationData.from_notification(user_notification.notification))
        )

    def check_being_expected_form(self) -> None:
        if (length := len(self.notification.visual_bindings)) != 1:
            raise_notify(f"This notification's visual_bindings length is {length}.")
        if (length := len(self.get_text_elements())) != 2:
            raise_notify(f"This notification's text_elements length is {length}.")

    def append_json(self, json_filepath: PathLike | str) -> None:
        try:
            with filelock.FileLock(str(json_filepath) + ".lock", timeout=1):
                with open(json_filepath, "a", encoding="utf-8") as f:
                    print(json.dumps(dataclasses.asdict(self), ensure_ascii=False), file=f, flush=True)
        except filelock.Timeout as e:
            print(f"filelock.Timeout: {e}\nSkipping UserNotificationData output to {json_filepath}")

    def get_text_elements(self) -> list[str]:
        return self.notification.visual_bindings[0].text_elements

    def get_app_user_model_id(self) -> str | None:
        if self.app_info is not None:
            return self.app_info.app_user_model_id
        else:
            return None

@dataclasses.dataclass
class AppInfoData:
    app_user_model_id: str
    display_info: AppDisplayInfoData
    id: str
    package_family_name: str

    @classmethod
    def from_app_info(cls, app_info: AppInfo) -> Self:
        return cls(
            try_default(lambda: app_info.app_user_model_id),
            try_default(lambda: AppDisplayInfoData.from_app_display_info(app_info.display_info)),
            try_default(lambda: app_info.id),
            try_default(lambda: app_info.package_family_name)
        )

@dataclasses.dataclass
class AppDisplayInfoData:
    description: str
    display_name: str

    @classmethod
    def from_app_display_info(cls, app_display_info: AppDisplayInfo) -> Self:
        return cls(
            try_default(lambda: app_display_info.description),
            try_default(lambda: app_display_info.display_name)
        )

@dataclasses.dataclass
class NotificationData:
    expiration_time: tuple[str, float]
    visual_bindings: list[NotificationBindingData]

    @classmethod
    def from_notification(cls, notification: Notification) -> Self:
        return cls(
            try_default(lambda: process_datetime(notification.expiration_time)), # type: ignore
            try_default(lambda: list(map(NotificationBindingData.from_notification_binding, notification.visual.bindings)))
        )

@dataclasses.dataclass
class NotificationBindingData:
    template: str
    text_elements: list[str]

    @classmethod
    def from_notification_binding(cls, notification_binding: NotificationBinding) -> Self:
        return cls(
            try_default(lambda: notification_binding.template),
            try_default(lambda: [adaptive_notification_text.text for adaptive_notification_text in notification_binding.get_text_elements()]),
        )

def try_default[T](f: Callable[[], T], default: Any = None) -> T:
    """この関数は返り値の型がAny(Noneを含む)になりうるが、返り値の型指定でそれを隠してタイプチェッカーを騙している"""
    try:
        return f()
    except Exception:
        return default

def process_datetime(dt: datetime.datetime) -> tuple[str, float]:
    return (dt.astimezone(zoneinfo.ZoneInfo("Japan")).strftime("%Y/%m/%d %H:%M:%S %Z"), dt.timestamp())


def get_notification_history(notification_history_id: str) -> Generator[ToastNotification]:
    for toast_notification in ToastNotificationManager.get_default().history.get_history_with_id(notification_history_id):
        yield toast_notification

def get_youtube_notification_history() -> Generator[YouTubeNotificationHistoryEntry]:
    for toast_notification in get_notification_history(edge_youtube_notification_history_id):
        yield YouTubeNotificationHistoryEntry(toast_notification)

def get_x_notification_history() -> Generator[XNotificationHistoryEntry]:
    for toast_notification in get_notification_history(edge_x_notification_history_id):
        yield XNotificationHistoryEntry(toast_notification)

def get_gmail_notification_history() -> Generator[GmailNotificationHistoryEntry]:
    for toast_notification in get_notification_history(edge_gmail_notification_history_id):
        yield GmailNotificationHistoryEntry(toast_notification)

type YTHisoryMatchDict = dict[Literal["youtube_id", "channel_long_id", "default"], str | None]

class YouTubeNotificationHistoryEntry:
    regex = re.compile(r"https://www\.youtube\.com/#1(?:(?P<youtube_id>[0-9A-Za-z_-]{10}[048AEIMQUYcgkosw])|(?P<channel_long_id>UC[0-9A-Za-z_-]{21}[AQgw])|(?P<default>default)|(?P<error>user_visible_auto_notification)|(?P<gift_channel_long_id>SPONSORSHIPS_GIFT_RECEIVED-UC[0-9A-Za-z_-]{21}[AQgw]))$")
    # youtube_idの部分は、shortsのとき"UC+channel_id(22 chars)", membersのとき"deafult"になっている。
    # https://webapps.stackexchange.com/a/101153
    def __init__(self, toast_notification: ToastNotification) -> None:
        xml_document = toast_notification.content
        self.texts = [text.inner_text for text in xml_document.get_elements_by_tag_name("text")]
        launch_attribute: str = xml_document.document_element.get_attribute("launch")
        if not (m := self.regex.search(launch_attribute)):
            raise_notify(f"Unexpected launch attribute: {launch_attribute}")
        self.match_dict: YTHisoryMatchDict = typing.cast(YTHisoryMatchDict, m.groupdict())
        #
        self.display_timestamp = datetime.datetime.fromisoformat(xml_document.document_element.get_attribute("displayTimestamp"))
        """aware (UTC)"""

class XNotificationHistoryEntry:
    regex = re.compile(r'--notification-launch-id="?0\|0\|(?P<edge_profile_name>.*)\|MSEdge\|0\|https://x\.com/\|p#https://x\.com/#1(?:tweet|self_thread)-(?P<x_id>[0-9]*)"?')
    def __init__(self, toast_notification: ToastNotification) -> None:
        xml_document = toast_notification.content
        # chromeの通知にはplacement="attribution"をつけたtext elementでその通知を送信したウェブサイト名が追加される。get_attribute()は指定したattributeがない場合空文字列を返す。
        self.texts = [text.inner_text for text in xml_document.get_elements_by_tag_name("text") if text.as_(XmlElement).get_attribute("placement") != "attribution"]
        launch_attribute: str = xml_document.document_element.get_attribute("launch")
        if not (m := self.regex.fullmatch(launch_attribute)):
            raise_notify(f"Unexpected launch attribute: {launch_attribute}")
        self.x_id = m["x_id"]
        self.edge_profile_name = m["edge_profile_name"]
        self.display_timestamp = datetime.datetime.fromisoformat(xml_document.document_element.get_attribute("displayTimestamp"))
        """aware (UTC)"""

class GmailNotificationHistoryEntry:
    def __init__(self, toast_notification: ToastNotification) -> None:
        xml_document = toast_notification.content
        self.texts = [text.inner_text for text in xml_document.get_elements_by_tag_name("text")]
        self.display_timestamp = datetime.datetime.fromisoformat(xml_document.document_element.get_attribute("displayTimestamp"))
        """aware (UTC)"""

class NotificationHistoryEntry(Protocol):
    texts: list[str]

class NotificationUserAndHistory(ABC):
    @abstractmethod
    def get_user_notification_delay(self) -> float:
        raise NotImplementedError

@dataclasses.dataclass
class YouTubeNotificationUserAndHistory(NotificationUserAndHistory):
    youtube_notification: YouTubeNotification
    history_entry: YouTubeNotificationHistoryEntry

    def get_user_notification_delay(self) -> float:
        return self.youtube_notification.user_notification_data.creation_time[1] - self.history_entry.display_timestamp.timestamp()

@dataclasses.dataclass
class XNotificationUserAndHistory(NotificationUserAndHistory):
    user_notification_data: UserNotificationData
    history_entry: XNotificationHistoryEntry

    def get_user_notification_delay(self) -> float:
        return self.user_notification_data.creation_time[1] - self.history_entry.display_timestamp.timestamp()

@dataclasses.dataclass
class TwitchGmailNotificationUserAndHistory(NotificationUserAndHistory):
    twitch_gmail_notification: TwitchGmailNotification
    history_entry: GmailNotificationHistoryEntry

    def get_user_notification_delay(self) -> float:
        return self.twitch_gmail_notification.user_notification_data.creation_time[1] - self.history_entry.display_timestamp.timestamp()

@dataclasses.dataclass
class GmailNotificationUserAndHistory(NotificationUserAndHistory):
    user_notification_data: UserNotificationData
    history_entry: GmailNotificationHistoryEntry

    def get_user_notification_delay(self) -> float:
        return self.user_notification_data.creation_time[1] - self.history_entry.display_timestamp.timestamp()

def find_corresponding_history_entry[T: NotificationHistoryEntry](history: Iterable[T], user_notification_data: UserNotificationData, convert: Callable[[list[str]], list[str]] | None = None) -> T | None:
    text_elements = user_notification_data.get_text_elements()
    if convert is not None:
        text_elements = convert(text_elements)
    for history_entry in history:
        if history_entry.texts == text_elements:
            return history_entry
    else:
        return None

def _x_convert(src: list[str]) -> list[str]:
    retval = src.copy()
    if retval[1] == "\n\t\t\t":
        retval[1] = ""
    return retval

def analyze_edge_notification(user_notification_data: UserNotificationData) -> YouTubeNotificationUserAndHistory | Literal["youtube_error"] | XNotificationUserAndHistory | TwitchGmailNotificationUserAndHistory | GmailNotificationUserAndHistory | None:
    """app_user_model_idがedgeであるuser_notification_dataについて、そのuser_notification_dataのtext_elementから判断できるデータの種類と、text_elementと一致するtextを持つhistoryの要素を取得して、対応したオブジェクトにまとめて返す。app_user_model_idがedgeでないときNoneを返す。app_user_model_idがedgeだがhistoryに対応する要素がないときexceptionをraiseする。"""
    if user_notification_data.get_app_user_model_id() != edge_user_model_id:
        return None
    if (youtube_notification := YouTubeNotification.from_user_notification_data(user_notification_data)) is not None:
        if (history_entry := find_corresponding_history_entry(get_youtube_notification_history(), user_notification_data)) is not None:
            if youtube_notification == "youtube_error":
                return "youtube_error"
            else:
                return YouTubeNotificationUserAndHistory(youtube_notification, history_entry)
        else:
            raise_notify(f"YouTube notification {user_notification_data.get_text_elements()} does not have corresponding youtube history entry.")
    elif (twitch_gmail_notification := TwitchGmailNotification.from_user_notification_data(user_notification_data)) is not None:
        if (history_entry := find_corresponding_history_entry(get_gmail_notification_history(), user_notification_data)) is not None:
            return TwitchGmailNotificationUserAndHistory(twitch_gmail_notification, history_entry)
        else:
            raise_notify(f"Twitch gmail notification {user_notification_data.get_text_elements()} does not have corresponding gmail history entry.")
    else:
        # X notification?
        if (history_entry := find_corresponding_history_entry(get_x_notification_history(), user_notification_data, _x_convert)) is not None:
            return XNotificationUserAndHistory(user_notification_data, history_entry)
        else:
            # Youtube notificatinまたはGamil notificationの可能性がある
            if find_corresponding_history_entry(get_youtube_notification_history(), user_notification_data) is not None:
                raise_notify(f"Unknown YouTube notification text pattern: {user_notification_data.get_text_elements()}. This notification maybe includes an unknown channel name.")
            elif (history_entry := find_corresponding_history_entry(get_gmail_notification_history(), user_notification_data)) is not None:
                return GmailNotificationUserAndHistory(user_notification_data, history_entry)
            else:
                raise_notify(f"Edge notification {user_notification_data.get_text_elements()} does not have corresponding YouTube, X or Gmail history entry.")

def show_notification(displayed_id: str, lines: Sequence[str] | str):
    if isinstance(lines, str):
        lines = [lines]
    toast_notifier = ToastNotificationManager.create_toast_notifier_with_id(displayed_id)
    toast_xml = ToastNotificationManager.get_template_content(ToastTemplateType.TOAST_TEXT02)
    text_tags = toast_xml.get_elements_by_tag_name("text")
    if len(lines) > 2:
        print(f"The number of lines is over 2. Lines after 2nd line will be ignored.\n{lines}")
    for i in range(2):
        text_tags[i].inner_text = lines[i] if i < len(lines) else ""
    toast_notifier.show(ToastNotification(toast_xml))

default_displayed_id: str = "notification_processor.py"

def print_notify(lines: Sequence[str] | str, displayed_id: str = default_displayed_id) -> None:
    if isinstance(lines, str):
        lines = [lines]
    show_notification(displayed_id, lines)
    print(*lines, sep="\n")

def raise_notify(lines: Sequence[str] | str, displayed_id: str = default_displayed_id) -> Never:
    """linesは", ".join(lines)でエラーに表示される。1行にすることを推奨。"""
    if isinstance(lines, str):
        lines = [lines]
    show_notification(displayed_id, lines)
    raise Exception(", ".join(lines))

def process_notification(notification_id: int, output_json_file: PathLike | str = notificatoin_data_json_filepath) -> None:
    user_notification_listener = UserNotificationListener.current
    access_status = user_notification_listener.get_access_status()
    if access_status.name != "ALLOWED":
        raise_notify(f"UserNotificationListener access: {access_status.name}")
    user_notification = user_notification_listener.get_notification(notification_id)
    if user_notification is None:
        print("user_notification is None")
        return
    user_notification_data = UserNotificationData.from_user_notification(user_notification)
    user_notification_data.append_json(output_json_file)
    print(user_notification_data.creation_time[0], user_notification_data.get_text_elements())
    user_notification_data.check_being_expected_form()

    if (notif_user_and_history := analyze_edge_notification(user_notification_data)) is not None:
        if notif_user_and_history == "youtube_error":
            user_notification_listener.remove_notification(notification_id)
            return

        delay = notif_user_and_history.get_user_notification_delay()
        if delay >= 10:
            print_notify([f"user_notification_delay: {delay}s", ": ".join(user_notification_data.get_text_elements()).replace("\n", " \\ ")])
        else:
            print(f"user_notification_delay: {delay}s")

        if isinstance(notif_user_and_history, YouTubeNotificationUserAndHistory):
            yt_notification = notif_user_and_history.youtube_notification
            print(f"is youtube: channel: {yt_notification.channel_name}, title: {yt_notification.title}, type: {yt_notification.content_type}")

        elif isinstance(notif_user_and_history, TwitchGmailNotificationUserAndHistory):
            channel_name = notif_user_and_history.twitch_gmail_notification.channel_name
            go_live_comment = notif_user_and_history.twitch_gmail_notification.go_live_comment
            print(f"is twitch: channel_name: {channel_name}, go_live_comment: {go_live_comment}")
            user_notification_listener.remove_notification(notification_id)
            show_notification("Twitch", (f"{channel_name}: Twitch live", go_live_comment))

        elif isinstance(notif_user_and_history, XNotificationUserAndHistory):
            print(f"is X: display_timestamp: {notif_user_and_history.history_entry.display_timestamp.astimezone(zoneinfo.ZoneInfo("Japan"))}, edge_profile: {notif_user_and_history.history_entry.edge_profile_name}")

        elif isinstance(notif_user_and_history, GmailNotificationUserAndHistory):
            print("is Gmail")
            user_notification_listener.remove_notification(notification_id)
            show_notification("Gmail", notif_user_and_history.user_notification_data.get_text_elements())

        else:
            assert_never(notif_user_and_history)

    elif user_notification_data.get_app_user_model_id() == discord_user_model_id:
        show_notification("Discord", user_notification_data.get_text_elements())

def main() -> None:
    process_notification(int(sys.argv[1]))

if __name__ == "__main__":
    main()
