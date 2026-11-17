DRIVELAN

Shared folders on the local network, without the cloud and without complexity.

DriveLan is an open-source desktop application for Windows and Linux that allows users to create shared folders on the local area network (LAN) and to access folders shared by other users in a simple and secure manner. It is intended as an alternative to native Windows file sharing (SMB) and to cloud storage services. Files remain within the local network, and users are not required to configure system permissions, map network drives, or know IP addresses.

PROJECT STATUS: Under development. The specification (Product Requirements Document, Technical Decisions, and Functional Specification Document) has been completed, and implementation is in progress. No version has been released to date.


1. INTENDED AUDIENCE

DriveLan is designed for small offices, computer laboratories, and classrooms, which are environments in which several people must exchange files on a daily basis, frequently without technical expertise. For this reason, the user interface is written entirely in Brazilian Portuguese, using clear language and avoiding technical jargon.


2. HOW IT WORKS

Each computer running DriveLan may operate in two roles simultaneously:

- Folder Owner: creates a shared folder, defines a six-digit PIN and a size limit, and manages the users who are connected to it.
- Client: locates the folders available on the network and joins them by entering the PIN provided by the folder owner.

Each person uses a local account, identified as name@computer. There is no central server; the computers on the network discover one another automatically.


3. MAIN FEATURES

- Automatic discovery of folders on the local network, with the option of adding a computer manually.
- PIN-based access: local accounts are protected by a PIN, accounts are locked after five failed attempts, and each folder is protected by a six-digit PIN.
- Encrypted communication: all network traffic is transmitted over TLS, using a dedicated certificate on each computer.
- User management: the folder owner can view the connected users and may disconnect or block them.
- File editing in the operating system's default application, with an "in editing" notice displayed to other users and a conflict copy created when necessary.
- A 30-day recycle bin for the recovery of deleted files.
- A 12-month audit log recording the actions performed by each user in each folder.
- Scheduled folder closure, with a deadline and a countdown displayed to users.
- Notifications of relevant events and an icon in the system tray.
- Persistence: automatic startup with the operating system and automatic reconnection to folders.
- Administrator panel (Shift + F12), protected by a security key defined during installation, intended for IT support staff.
- Full compatibility between Windows and Linux: a folder created on one operating system may be used by clients running the other.

Features not included in the first version:
Virtual drive (for example, Z:), per-user permissions, search, version history, offline access, web interface, macOS support, and mobile support.


4. TECHNOLOGIES

- Programming language: Python 3.12
- User interface: PySide6 (Qt Widgets and QSS)
- Database: SQLite (stored locally on each computer)
- Networking: HTTP and WebSocket over TLS (aiohttp)
- Discovery: mDNS/DNS-SD, with UDP broadcast as a fallback mechanism
- Password and PIN hashing: Argon2id

The application runs as two separate processes: a system service (drivelan-service), which is responsible for networking, the database, and business rules; and the windowed application with a system tray icon (drivelan), which is used directly by the user.


5. PLATFORMS AND DISTRIBUTION

- Windows 10 and 11: .exe installer
- Linux: .rpm packages (Fedora and derivative distributions) and .deb packages (Debian, Ubuntu, and derivative distributions)

The installers will be published on the Releases page of this repository. Each version will undergo a pilot test in a real computer laboratory prior to its release.


6. DOCUMENTATION

The complete project specification is located in the docs directory:

- PRD_DriveLan.md: Product Requirements Document
- DECISOES_TECNICAS.md: architectural and technological decisions
- FSD.md: Functional Specification Document
- DESIGN.md: visual reference for the user interface


7. CONTRIBUTING

DriveLan is a community project, and contributions are welcome. These include bug fixes, testing on different networks and operating systems, user interface suggestions, translations, and documentation. To report a problem or propose an improvement, please open an issue. To submit changes, please open a pull request.


8. LICENSE

This project is distributed under the GNU General Public License, version 3 (GPLv3). Please refer to the LICENSE file for further details.
