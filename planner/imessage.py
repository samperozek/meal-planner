"""Send-only iMessage to the cook (config imessage.to) via the Messages app (AppleScript). No reading of the Messages database.

  python3 imessage.py "text to send"        sends to imessage.to in config.json
  python3 imessage.py --file message.txt    sends the contents of a file
  add --once-today KEY                     skip (prints ALREADY_SENT) if a message with KEY was already sent today
Every send is appended to sent_log.txt.
The first send makes macOS ask whether Claude may control Messages; click OK.
"""
import datetime as dt, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

HERE = os.path.dirname(os.path.abspath(__file__))
SENT_LOG = os.path.join(config.STATE, "sent_log.txt")

SCRIPT = '''on run argv
    set theHandle to item 1 of argv
    set theText to item 2 of argv
    tell application "Messages"
        set svc to 1st account whose service type = iMessage
        send theText to participant theHandle of svc
    end tell
end run'''


def send(text, key="-"):
    today = dt.date.today().isoformat()
    if key != "-" and os.path.exists(SENT_LOG):
        if any(l.startswith(today) and f"\t{key}\t" in l for l in open(SENT_LOG)):
            print(f"ALREADY_SENT {key} today"); return
    to = config.PHONE
    if not to:
        raise SystemExit("SEND_FAILED: set imessage.to in config.json")
    r = subprocess.run(["osascript", "-e", SCRIPT, to, text], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"SEND_FAILED: {r.stderr.strip()}")
    with open(SENT_LOG, "a") as f:
        f.write(f"{dt.datetime.now().isoformat(timespec='minutes')}\t{key}\t{text.splitlines()[0][:80]}\n")
    print(f"SENT to {to}")


if __name__ == "__main__":
    args, key = sys.argv[1:], "-"
    if "--once-today" in args:
        i = args.index("--once-today"); key = args[i + 1]; del args[i:i + 2]
    if len(args) == 2 and args[0] == "--file":
        send(open(args[1]).read().strip(), key)
    elif len(args) == 1:
        send(args[0], key)
    else:
        print(__doc__)
