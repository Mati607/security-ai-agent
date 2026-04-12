from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Tuple


@dataclass(frozen=True)
class CatalogTechnique:
    """Single technique row in the offline Enterprise catalogue."""

    technique_id: str
    name: str
    tactic_id: str
    keywords: Tuple[str, ...]


TECHNIQUES: Final[Tuple[CatalogTechnique, ...]] = (
    CatalogTechnique(
        technique_id="T1566",
        name="Phishing",
        tactic_id="TA0001",
        keywords=(
            "phishing",
            "spear phishing",
            "malicious attachment",
            "html smuggling",
            "credential harvest page",
        ),
    ),
    CatalogTechnique(
        technique_id="T1190",
        name="Exploit Public-Facing Application",
        tactic_id="TA0001",
        keywords=(
            "exploit",
            "cve-",
            "rce",
            "remote code",
            "sql injection",
            "ssrf",
            "deserialization vulnerability",
        ),
    ),
    CatalogTechnique(
        technique_id="T1133",
        name="External Remote Services",
        tactic_id="TA0001",
        keywords=(
            "vpn",
            "rdp gateway",
            "citrix",
            "remote desktop published",
        ),
    ),
    CatalogTechnique(
        technique_id="T1078",
        name="Valid Accounts",
        tactic_id="TA0006",
        keywords=(
            "stolen credentials",
            "password spray",
            "brute force login",
            "golden ticket",
            "silver ticket",
            "pass the hash",
            "kerberoast",
        ),
    ),
    CatalogTechnique(
        technique_id="T1091",
        name="Replication Through Removable Media",
        tactic_id="TA0008",
        keywords=(
            "usb",
            "removable media",
            "autorun.inf",
        ),
    ),
    CatalogTechnique(
        technique_id="T1210",
        name="Exploitation of Remote Services",
        tactic_id="TA0008",
        keywords=(
            "eternalblue",
            "smb exploit",
            "rpc exploit",
            "remote service exploit",
        ),
    ),
    CatalogTechnique(
        technique_id="T1021",
        name="Remote Services",
        tactic_id="TA0008",
        keywords=(
            "rdp session",
            "ssh tunnel",
            "winrm remote",
            "psexec",
            "remote powershell",
        ),
    ),
    CatalogTechnique(
        technique_id="T1550",
        name="Use Alternate Authentication Material",
        tactic_id="TA0008",
        keywords=(
            "pass the ticket",
            "forged ticket",
            "stolen ticket",
        ),
    ),
    CatalogTechnique(
        technique_id="T1218",
        name="Signed Binary Proxy Execution",
        tactic_id="TA0005",
        keywords=(
            "mshta",
            "rundll32",
            "regsvr32",
            "odbcconf",
            "installutil",
            "regsvcs",
        ),
    ),
    CatalogTechnique(
        technique_id="T1216",
        name="Signed Script Proxy Execution",
        tactic_id="TA0005",
        keywords=(
            "pubprn",
            "slmgr",
            "infdefaultinstall",
        ),
    ),
    CatalogTechnique(
        technique_id="T1059",
        name="Command and Scripting Interpreter",
        tactic_id="TA0002",
        keywords=(
            "powershell",
            "pwsh",
            "cmd.exe",
            "bash -c",
            "wscript",
            "cscript",
            "python -c",
        ),
    ),
    CatalogTechnique(
        technique_id="T1059.001",
        name="PowerShell",
        tactic_id="TA0002",
        keywords=(
            "powershell",
            "encodedcommand",
            "-enc",
            "invoke-expression",
            "iex(",
        ),
    ),
    CatalogTechnique(
        technique_id="T1059.003",
        name="Windows Command Shell",
        tactic_id="TA0002",
        keywords=(
            "cmd.exe",
            "cmd /c",
            "batch script",
            ".bat malicious",
        ),
    ),
    CatalogTechnique(
        technique_id="T1059.005",
        name="Visual Basic",
        tactic_id="TA0002",
        keywords=(
            "vbscript",
            "wscript",
            "mshta vbscript",
        ),
    ),
    CatalogTechnique(
        technique_id="T1106",
        name="Native API",
        tactic_id="TA0002",
        keywords=(
            "ntdll",
            "syscall direct",
            "unhook ntdll",
        ),
    ),
    CatalogTechnique(
        technique_id="T1047",
        name="Windows Management Instrumentation",
        tactic_id="TA0002",
        keywords=(
            "wmi",
            "wmic",
            "__eventfilter",
            "root\\subscription",
        ),
    ),
    CatalogTechnique(
        technique_id="T1129",
        name="Shared Modules",
        tactic_id="TA0002",
        keywords=(
            "dll load",
            "reflective dll",
            "module stomping",
        ),
    ),
    CatalogTechnique(
        technique_id="T1204",
        name="User Execution",
        tactic_id="TA0002",
        keywords=(
            "user opened",
            "double-click",
            "macro enabled",
            "enable content",
        ),
    ),
    CatalogTechnique(
        technique_id="T1203",
        name="Exploitation for Client Execution",
        tactic_id="TA0002",
        keywords=(
            "exploit kit",
            "browser exploit",
            "flash exploit",
        ),
    ),
    CatalogTechnique(
        technique_id="T1053",
        name="Scheduled Task/Job",
        tactic_id="TA0003",
        keywords=(
            "schtasks",
            "at.exe",
            "cron job",
            "task scheduler",
            "scheduled task",
        ),
    ),
    CatalogTechnique(
        technique_id="T1547",
        name="Boot or Logon Autostart Execution",
        tactic_id="TA0003",
        keywords=(
            "run keys",
            "startup folder",
            "logon script",
        ),
    ),
    CatalogTechnique(
        technique_id="T1543",
        name="Create or Modify System Process",
        tactic_id="TA0003",
        keywords=(
            "windows service",
            "new-service",
            "sc create",
            "systemctl enable",
        ),
    ),
    CatalogTechnique(
        technique_id="T1136",
        name="Create Account",
        tactic_id="TA0003",
        keywords=(
            "net user /add",
            "local account created",
            "new user added",
        ),
    ),
    CatalogTechnique(
        technique_id="T1078.002",
        name="Domain Accounts",
        tactic_id="TA0003",
        keywords=(
            "domain admin login",
            "privileged ad account",
        ),
    ),
    CatalogTechnique(
        technique_id="T1546",
        name="Event Triggered Execution",
        tactic_id="TA0003",
        keywords=(
            "wmi event",
            "screensaver hijack",
            "netsh helper",
        ),
    ),
    CatalogTechnique(
        technique_id="T1036",
        name="Masquerading",
        tactic_id="TA0005",
        keywords=(
            "rename binary",
            "fake process name",
            "right-to-left override",
            "spoofed parent",
        ),
    ),
    CatalogTechnique(
        technique_id="T1027",
        name="Obfuscated Files or Information",
        tactic_id="TA0005",
        keywords=(
            "base64 decode",
            "xor encoded",
            "gzip payload",
            "encrypted shellcode",
        ),
    ),
    CatalogTechnique(
        technique_id="T1140",
        name="Deobfuscate/Decode Files or Information",
        tactic_id="TA0005",
        keywords=(
            "decode payload",
            "unpack malware",
            "decrypt config",
        ),
    ),
    CatalogTechnique(
        technique_id="T1497",
        name="Virtualization/Sandbox Evasion",
        tactic_id="TA0005",
        keywords=(
            "sandbox evasion",
            "vm check",
            "sleep obfuscation",
        ),
    ),
    CatalogTechnique(
        technique_id="T1562",
        name="Impair Defenses",
        tactic_id="TA0005",
        keywords=(
            "disable defender",
            "tamper protection off",
            "firewall disabled",
            "logging stopped",
        ),
    ),
    CatalogTechnique(
        technique_id="T1070",
        name="Indicator Removal",
        tactic_id="TA0005",
        keywords=(
            "clear logs",
            "wevtutil cl",
            "rm -rf /var/log",
            "timestomp",
        ),
    ),
    CatalogTechnique(
        technique_id="T1112",
        name="Modify Registry",
        tactic_id="TA0005",
        keywords=(
            "registry run key",
            "uac bypass registry",
            "persistence registry",
        ),
    ),
    CatalogTechnique(
        technique_id="T1055",
        name="Process Injection",
        tactic_id="TA0005",
        keywords=(
            "dll injection",
            "process hollowing",
            "apc inject",
            "thread hijack",
        ),
    ),
    CatalogTechnique(
        technique_id="T1574",
        name="Hijack Execution Flow",
        tactic_id="TA0005",
        keywords=(
            "dll search order hijack",
            "path interception",
            "com hijack",
        ),
    ),
    CatalogTechnique(
        technique_id="T1548",
        name="Abuse Elevation Control Mechanism",
        tactic_id="TA0004",
        keywords=(
            "uac bypass",
            "token manipulation",
            "elevation gui",
        ),
    ),
    CatalogTechnique(
        technique_id="T1068",
        name="Exploitation for Privilege Escalation",
        tactic_id="TA0004",
        keywords=(
            "local privilege escalation",
            "kernel exploit",
            "tokenkidnap",
            "zero-day kernel",
            "cve kernel exploit",
        ),
    ),
    CatalogTechnique(
        technique_id="T1134",
        name="Access Token Manipulation",
        tactic_id="TA0004",
        keywords=(
            "duplicate token",
            "impersonate token",
            "primary token",
        ),
    ),
    CatalogTechnique(
        technique_id="T1003",
        name="OS Credential Dumping",
        tactic_id="TA0006",
        keywords=(
            "lsass dump",
            "mimikatz",
            "sekurlsa",
            "sam hive",
            "ntds.dit",
            "dcsync",
        ),
    ),
    CatalogTechnique(
        technique_id="T1003.001",
        name="LSASS Memory",
        tactic_id="TA0006",
        keywords=(
            "lsass",
            "procdump lsass",
            "comsvcs.dll minidump",
        ),
    ),
    CatalogTechnique(
        technique_id="T1003.003",
        name="NTDS",
        tactic_id="TA0006",
        keywords=(
            "ntds.dit",
            "secretsdump",
            "drsuapi",
        ),
    ),
    CatalogTechnique(
        technique_id="T1558",
        name="Steal or Forge Kerberos Tickets",
        tactic_id="TA0006",
        keywords=(
            "kerberoast",
            "as-rep roast",
            "golden ticket",
        ),
    ),
    CatalogTechnique(
        technique_id="T1110",
        name="Brute Force",
        tactic_id="TA0006",
        keywords=(
            "password brute",
            "hydra",
            "credential stuffing",
            "spray attack",
        ),
    ),
    CatalogTechnique(
        technique_id="T1556",
        name="Modify Authentication Process",
        tactic_id="TA0006",
        keywords=(
            "patch lsass",
            "ssp dll",
            "authentication package",
        ),
    ),
    CatalogTechnique(
        technique_id="T1040",
        name="Network Sniffing",
        tactic_id="TA0006",
        keywords=(
            "packet capture",
            "promiscuous mode",
            "sniff credentials",
        ),
    ),
    CatalogTechnique(
        technique_id="T1083",
        name="File and Directory Discovery",
        tactic_id="TA0007",
        keywords=(
            "directory listing",
            "dir /s",
            "find sensitive files",
        ),
    ),
    CatalogTechnique(
        technique_id="T1018",
        name="Remote System Discovery",
        tactic_id="TA0007",
        keywords=(
            "net view",
            "arp -a",
            "ping sweep",
            "ad computers",
        ),
    ),
    CatalogTechnique(
        technique_id="T1016",
        name="System Network Configuration Discovery",
        tactic_id="TA0007",
        keywords=(
            "ipconfig",
            "ifconfig",
            "route print",
            "netstat",
        ),
    ),
    CatalogTechnique(
        technique_id="T1049",
        name="System Network Connections Discovery",
        tactic_id="TA0007",
        keywords=(
            "netstat -ano",
            "ss -tunap",
            "active connections",
        ),
    ),
    CatalogTechnique(
        technique_id="T1082",
        name="System Information Discovery",
        tactic_id="TA0007",
        keywords=(
            "systeminfo",
            "uname",
            "wmic os get",
        ),
    ),
    CatalogTechnique(
        technique_id="T1012",
        name="Query Registry",
        tactic_id="TA0007",
        keywords=(
            "reg query",
            "registry enumeration",
        ),
    ),
    CatalogTechnique(
        technique_id="T1057",
        name="Process Discovery",
        tactic_id="TA0007",
        keywords=(
            "tasklist",
            "ps aux",
            "wmic process",
        ),
    ),
    CatalogTechnique(
        technique_id="T1518",
        name="Software Discovery",
        tactic_id="TA0007",
        keywords=(
            "installed software",
            "wmic product",
        ),
    ),
    CatalogTechnique(
        technique_id="T1560",
        name="Archive Collected Data",
        tactic_id="TA0009",
        keywords=(
            "7z a",
            "rar a",
            "zip password",
            "archive staging",
        ),
    ),
    CatalogTechnique(
        technique_id="T1005",
        name="Data from Local System",
        tactic_id="TA0009",
        keywords=(
            "collect files",
            "copy sensitive",
            "document harvest",
        ),
    ),
    CatalogTechnique(
        technique_id="T1114",
        name="Email Collection",
        tactic_id="TA0009",
        keywords=(
            "outlook pst",
            "mailbox export",
            "owa scrape",
        ),
    ),
    CatalogTechnique(
        technique_id="T1025",
        name="Data from Removable Media",
        tactic_id="TA0009",
        keywords=(
            "usb exfil",
            "copy to thumb drive",
        ),
    ),
    CatalogTechnique(
        technique_id="T1071",
        name="Application Layer Protocol",
        tactic_id="TA0011",
        keywords=(
            "https beacon",
            "dns tunnel",
            "http c2",
            "telegram api",
        ),
    ),
    CatalogTechnique(
        technique_id="T1071.001",
        name="Web Protocols",
        tactic_id="TA0011",
        keywords=(
            "https callback",
            "user-agent beacon",
            "cookie c2",
        ),
    ),
    CatalogTechnique(
        technique_id="T1071.004",
        name="DNS",
        tactic_id="TA0011",
        keywords=(
            "dns tunnel",
            "dns query encoded",
            "doh c2",
        ),
    ),
    CatalogTechnique(
        technique_id="T1095",
        name="Non-Application Layer Protocol",
        tactic_id="TA0011",
        keywords=(
            "icmp tunnel",
            "raw socket c2",
        ),
    ),
    CatalogTechnique(
        technique_id="T1105",
        name="Ingress Tool Transfer",
        tactic_id="TA0011",
        keywords=(
            "bitsadmin",
            "certutil -urlcache",
            "wget malicious",
            "curl http malware",
        ),
    ),
    CatalogTechnique(
        technique_id="T1573",
        name="Encrypted Channel",
        tactic_id="TA0011",
        keywords=(
            "tls beacon",
            "ssl pinning bypass",
            "encrypted c2",
        ),
    ),
    CatalogTechnique(
        technique_id="T1090",
        name="Proxy",
        tactic_id="TA0011",
        keywords=(
            "proxychains",
            "socks proxy",
            "tor connection",
        ),
    ),
    CatalogTechnique(
        technique_id="T1219",
        name="Remote Access Software",
        tactic_id="TA0011",
        keywords=(
            "anydesk",
            "teamviewer",
            "screenconnect",
            "logmein abuse",
        ),
    ),
    CatalogTechnique(
        technique_id="T1001",
        name="Data Obfuscation",
        tactic_id="TA0011",
        keywords=(
            "jitter beacon",
            "protocol smuggling",
            "steganography c2",
        ),
    ),
    CatalogTechnique(
        technique_id="T1048",
        name="Exfiltration Over Alternative Protocol",
        tactic_id="TA0010",
        keywords=(
            "ftp exfil",
            "smtp exfil",
            "icmp exfil",
        ),
    ),
    CatalogTechnique(
        technique_id="T1041",
        name="Exfiltration Over C2 Channel",
        tactic_id="TA0010",
        keywords=(
            "exfiltrate via beacon",
            "slow data theft",
        ),
    ),
    CatalogTechnique(
        technique_id="T1567",
        name="Exfiltration Over Web Service",
        tactic_id="TA0010",
        keywords=(
            "dropbox exfil",
            "onedrive upload",
            "pastebin post",
        ),
    ),
    CatalogTechnique(
        technique_id="T1486",
        name="Data Encrypted for Impact",
        tactic_id="TA0040",
        keywords=(
            "ransomware",
            "encrypted files",
            ".encrypted extension",
            "lockbit",
            "blackcat",
            "ryuk",
        ),
    ),
    CatalogTechnique(
        technique_id="T1489",
        name="Service Stop",
        tactic_id="TA0040",
        keywords=(
            "stop service",
            "disable backup service",
            "sql service stopped",
        ),
    ),
    CatalogTechnique(
        technique_id="T1490",
        name="Inhibit System Recovery",
        tactic_id="TA0040",
        keywords=(
            "vssadmin delete shadows",
            "wbadmin delete",
            "recovery disabled",
        ),
    ),
    CatalogTechnique(
        technique_id="T1491",
        name="Defacement",
        tactic_id="TA0040",
        keywords=(
            "website defaced",
            "index.html replaced",
        ),
    ),
    CatalogTechnique(
        technique_id="T1498",
        name="Network Denial of Service",
        tactic_id="TA0040",
        keywords=(
            "ddos",
            "syn flood",
            "volumetric attack",
        ),
    ),
    CatalogTechnique(
        technique_id="T1499",
        name="Endpoint Denial of Service",
        tactic_id="TA0040",
        keywords=(
            "cpu exhaustion",
            "fork bomb",
            "resource exhaustion",
        ),
    ),
    CatalogTechnique(
        technique_id="T1531",
        name="Account Access Removal",
        tactic_id="TA0040",
        keywords=(
            "password changed mass",
            "account lockout attack",
        ),
    ),
    CatalogTechnique(
        technique_id="T1195",
        name="Supply Chain Compromise",
        tactic_id="TA0042",
        keywords=(
            "compromised update",
            "vendor breach",
            "signed malicious update",
        ),
    ),
    CatalogTechnique(
        technique_id="T1583",
        name="Acquire Infrastructure",
        tactic_id="TA0042",
        keywords=(
            "bulletproof hosting",
            "c2 domain purchase",
            "vps rented",
        ),
    ),
    CatalogTechnique(
        technique_id="T1586",
        name="Compromise Accounts",
        tactic_id="TA0042",
        keywords=(
            "compromised email account",
            "hijacked social",
        ),
    ),
    CatalogTechnique(
        technique_id="T1595",
        name="Active Scanning",
        tactic_id="TA0043",
        keywords=(
            "vulnerability scan",
            "port scan",
            "nmap -sS",
            "masscan",
        ),
    ),
    CatalogTechnique(
        technique_id="T1592",
        name="Gather Victim Host Information",
        tactic_id="TA0043",
        keywords=(
            "whois lookup",
            "dns recon",
            "shodan",
        ),
    ),
    CatalogTechnique(
        technique_id="T1590",
        name="Gather Victim Network Information",
        tactic_id="TA0043",
        keywords=(
            "asn lookup",
            "ip range recon",
        ),
    ),
    CatalogTechnique(
        technique_id="T1588",
        name="Obtain Capabilities",
        tactic_id="TA0042",
        keywords=(
            "buy exploit",
            "malware as a service",
            "rent c2",
        ),
    ),
    CatalogTechnique(
        technique_id="T1552",
        name="Unsecured Credentials",
        tactic_id="TA0006",
        keywords=(
            "cleartext password",
            "config file password",
            ".env secret",
        ),
    ),
    CatalogTechnique(
        technique_id="T1552.001",
        name="Credentials In Files",
        tactic_id="TA0006",
        keywords=(
            "web.config password",
            "bash history password",
            "keys in repo",
        ),
    ),
    CatalogTechnique(
        technique_id="T1187",
        name="Forced Authentication",
        tactic_id="TA0006",
        keywords=(
            "responder",
            "llmnr poison",
            "ntlm relay coerce",
        ),
    ),
    CatalogTechnique(
        technique_id="T1189",
        name="Drive-by Compromise",
        tactic_id="TA0001",
        keywords=(
            "malvertising",
            "drive-by download",
            "watering hole",
        ),
    ),
    CatalogTechnique(
        technique_id="T1200",
        name="Hardware Additions",
        tactic_id="TA0001",
        keywords=(
            "rogue usb device",
            "badusb",
            "planted hardware",
        ),
    ),
    CatalogTechnique(
        technique_id="T1098",
        name="Account Manipulation",
        tactic_id="TA0003",
        keywords=(
            "add ad group member",
            "reset user password attacker",
            "delegate rights",
        ),
    ),
    CatalogTechnique(
        technique_id="T1222",
        name="File and Directory Permissions Modification",
        tactic_id="TA0005",
        keywords=(
            "icacls",
            "chmod 777",
            "weak acl",
        ),
    ),
    CatalogTechnique(
        technique_id="T1222.001",
        name="Windows File and Directory Permissions Modification",
        tactic_id="TA0005",
        keywords=(
            "takeown",
            "cacls everyone",
        ),
    ),
    CatalogTechnique(
        technique_id="T1564",
        name="Hide Artifacts",
        tactic_id="TA0005",
        keywords=(
            "hidden file",
            "attrib +h",
            "hidden volume",
        ),
    ),
    CatalogTechnique(
        technique_id="T1562.001",
        name="Disable or Modify Tools",
        tactic_id="TA0005",
        keywords=(
            "disable edr",
            "kill av process",
            "unload driver",
        ),
    ),
    CatalogTechnique(
        technique_id="T1021.001",
        name="Remote Desktop Protocol",
        tactic_id="TA0008",
        keywords=(
            "rdp connection",
            "mstsc",
            "terminal services",
        ),
    ),
    CatalogTechnique(
        technique_id="T1021.002",
        name="SMB/Windows Admin Shares",
        tactic_id="TA0008",
        keywords=(
            "admin$ share",
            "c$ share",
            "ipc$ connection",
        ),
    ),
    CatalogTechnique(
        technique_id="T1021.006",
        name="Windows Remote Management",
        tactic_id="TA0008",
        keywords=(
            "winrm",
            "enter-pssession",
            "wsmprovhost",
        ),
    ),
    CatalogTechnique(
        technique_id="T1553",
        name="Subvert Trust Controls",
        tactic_id="TA0005",
        keywords=(
            "code signing bypass",
            "stolen cert",
            "weak signature check",
        ),
    ),
    CatalogTechnique(
        technique_id="T1553.002",
        name="Code Signing",
        tactic_id="TA0005",
        keywords=(
            "invalid signature",
            "self-signed malware",
        ),
    ),
    CatalogTechnique(
        technique_id="T1037",
        name="Boot or Logon Initialization Scripts",
        tactic_id="TA0003",
        keywords=(
            "logon script gpo",
            "startup script persistence",
        ),
    ),
    CatalogTechnique(
        technique_id="T1548.002",
        name="Bypass User Account Control",
        tactic_id="TA0004",
        keywords=(
            "uac bypass fodhelper",
            "eventvwr mmc",
        ),
    ),
    CatalogTechnique(
        technique_id="T1069",
        name="Permission Groups Discovery",
        tactic_id="TA0007",
        keywords=(
            "whoami /groups",
            "net group",
            "domain admins membership",
        ),
    ),
    CatalogTechnique(
        technique_id="T1056",
        name="Input Capture",
        tactic_id="TA0009",
        keywords=(
            "keylogger",
            "credential prompt phishing",
            "clipboard hook",
        ),
    ),
    CatalogTechnique(
        technique_id="T1113",
        name="Screen Capture",
        tactic_id="TA0009",
        keywords=(
            "screenshot malware",
            "desktop capture",
        ),
    ),
    CatalogTechnique(
        technique_id="T1123",
        name="Audio Capture",
        tactic_id="TA0009",
        keywords=(
            "microphone record",
            "audio stream",
        ),
    ),
    CatalogTechnique(
        technique_id="T1565",
        name="Data Manipulation",
        tactic_id="TA0040",
        keywords=(
            "data wipe",
            "database tamper",
            "integrity sabotage",
        ),
    ),
    CatalogTechnique(
        technique_id="T1496",
        name="Resource Hijacking",
        tactic_id="TA0040",
        keywords=(
            "cryptominer",
            "xmrig",
            "coinhive",
        ),
    ),
    CatalogTechnique(
        technique_id="T1584",
        name="Compromise Infrastructure",
        tactic_id="TA0042",
        keywords=(
            "compromised website",
            "c2 on legit host",
        ),
    ),
    CatalogTechnique(
        technique_id="T1598",
        name="Phishing for Information",
        tactic_id="TA0043",
        keywords=(
            "pretexting",
            "vishing",
            "credential harvest recon",
        ),
    ),
    CatalogTechnique(
        technique_id="T1597",
        name="Search Open Websites/Domains",
        tactic_id="TA0043",
        keywords=(
            "linkedin scrape",
            "github secret search",
            "google dork",
        ),
    ),
)
