# Installing and maintaining the ISO/IEC 42001 portal

How to get the portal running on your computer, how to connect it with your team and how to look after it afterwards
(backups, updating, problems). For using it, screen by screen, there is the [user manual](manual.md).

If something here sounds too technical (MySQL, port, server…), you don't need to understand all of it: those sections
tell you what to pass on to your IT person.

**If you have Claude Code** (see [Optional: AI (Claude)](#optional-ai-claude)), it can guide you step by step: open it
in the program folder and type "help me install the portal". It asks what you want to do, checks what it can (Python,
whether the MySQL can be reached) and guides you through the rest, including setting up the MySQL on Amazon,
Microsoft, Google or your own server. It doesn't create anything for you or ask for passwords: those are typed into the
portal. Without Claude Code, this manual is enough.

> **The portal's screens are in Spanish.** Chrome and Edge can translate them for you: click the translate icon in the
> address bar, or right-click on the page → "Translate to English". Some words may come out odd, because it is an
> automatic translation. This manual gives the names of buttons and screens in Spanish, with their meaning, so you can
> find them either way.

## Contents

1. [What you need](#what-you-need)
2. [Download and start](#download-and-start)
3. [Choose how you will use it](#choose-how-you-will-use-it)
4. [Only on this computer](#only-on-this-computer)
5. [Shared with your team](#shared-with-your-team)
6. [The MySQL: what to ask for](#the-mysql-what-to-ask-for)
7. [The files folder](#the-files-folder)
8. [Optional: AI (Claude)](#optional-ai-claude)
9. [Optional: email reminders (Outlook)](#optional-email-reminders-outlook)
10. [Backups](#backups)
11. [Updating to a new version](#updating-to-a-new-version)
12. [If the administrator forgets their password](#if-the-administrator-forgets-their-password)
13. [If something does not work](#if-something-does-not-work)
14. [Security](#security)
15. [Legal notice](#legal-notice)

---

## What you need

- **A Windows computer** (10 or 11). It does not work on Mac or Linux: starting it, the email reminders and the
  notifications are Windows features.
- **Python**, the language the portal is written in. It is free. If you don't have it, the portal tells you the first
  time and opens the download page (see [Download and start](#download-and-start)).
- **Internet the first time**, so the portal can download the parts it needs. After that, in the "only on this
  computer" mode, it works without internet.
- **Only if you share it with your team:** a MySQL database and a shared folder (see
  [Shared with your team](#shared-with-your-team)).
- **Optional:** Claude Code, for the AI help, and classic Outlook, for the email reminders. Without them, everything
  else works the same.

## Download and start

1. **Download the portal.** On the repository page on GitHub, [github.com/aracilpau/portal-iso42001](https://github.com/aracilpau/portal-iso42001), green button **«Code» → «Download ZIP»**.
2. **Unzip it** into a folder of yours, for example `C:\Portal ISO 42001`. This is the **program folder**. Your data
   does not go here: it goes in another folder, so that updating or deleting the program does not touch it.
3. **Double-click `arrancar.bat`**, inside that folder.
   - If a blue warning appears, "Windows protected your PC", click "More info" → "Run anyway". This happens with
     programs downloaded from the internet that are not signed by a company.
   - **If you don't have Python,** its download page opens. Install the latest version and, on the first screen of the
     installer, **tick "Add python.exe to PATH"** (otherwise the portal can't find it). Then double-click
     `arrancar.bat` again.
   - **The first time it takes a couple of minutes:** it prepares what it needs. After that, a few seconds.
4. **A black window opens, and the browser** with the portal. The black window is the portal running: **don't close
   it while you use it**. When you close it, the portal shuts down. The portal works only on your computer, even though
   you see it in the browser: it is not on the internet.

The first time, the portal shows you the installation: a couple of screens to choose how you will use it and to create
your account.

To shut it down, close the black window or double-click `parar.bat`.

## Choose how you will use it

The first screen lets you choose between two ways. Both have the same portal; what changes is where the data is kept
and who can get in.

| | Only on this computer | Shared with your team |
|---|---|---|
| **Where the data is** | In a folder on your computer | In a MySQL database; the files, in a shared folder |
| **What you need to install** | Nothing else | The MySQL, once for the whole team |
| **Who gets in** | Whoever uses this computer | The whole team, each from their own computer and with their own account |
| **Who it is for** | To get started, or if you handle it on your own | If there are several of you |

What you choose is saved on your computer, outside the program folder. That way, when you update, it does not ask
again.

## Only on this computer

1. Click **«Usarlo solo en este ordenador»** (Use it only on this computer).
2. **Where is the data saved?** By default, in `Documentos\Portal ISO 42001` (`Documents\Portal ISO 42001` on English
   Windows). If you don't know which to choose, leave that one. Everything you fill in and the evidence files go there.
3. **Your account and your company:** the company name, your name, your email and a password (at least 8 characters).
   You will sign in with the email and the password every time.
4. **«Crear y entrar»** (Create and sign in). You are in: the portal takes you to your company's questionnaire, a few
   questions to get started.

Your account is the **administrator** account: you can create more accounts and companies from **«Administrar»**
(Administer), at the top right (see the [user manual](manual.md), section `entrar`).

## Shared with your team

**If you are the first in the team:**

1. Get the MySQL (see [The MySQL: what to ask for](#the-mysql-what-to-ask-for)) and the shared folder (see
   [The files folder](#the-files-folder)).
2. In the portal, click **«Compartirlo con mi equipo»** (Share it with my team).
3. **What is your MySQL?** Type in the details given to you by whoever set it up: the server address, the port, the
   MySQL user and password (not your portal ones) and the database name. Click **«Probar conexión»** (Test
   connection): it tells you whether they work and, if not, why.
4. **The files folder:** click «Examinar…» (Browse…) and choose it.
5. **Your account and your company,** as in the "only on this computer" mode. Your account is the administrator one.
6. Create the others' accounts in **«Administrar»** and give each of them their email and password, and also the MySQL
   details (safely, see [Security](#security)).

**If your team already uses it:**

1. Ask whoever manages it for the MySQL details and your account (email and password).
2. Download and start the portal on your computer. Click **«Compartirlo con mi equipo»** and type in the MySQL details.
3. Choose the files folder: the same one the team uses, synced on your computer. The portal already knows your team
   uses it and tells you this is the last step: it does not create anything.
4. It takes you to «Entrar» (Sign in), with the message «Listo: el portal ya está conectado con el de tu equipo»
   (Done: the portal is now connected to your team's). Sign in with your email and your password.

The MySQL details are saved on your computer, in a file that only the portal uses. You don't need to open it or touch
it.

## The MySQL: what to ask for

The MySQL is the database where the portal keeps what the team fills in (accounts, companies, tracking, Statement of
Applicability…), so that everyone sees the same thing. It works like a central filing cabinet: each computer looks
things up and saves in it. It is set up **once for the whole team**. If you don't know how to set it up, ask your IT
person or whoever runs your servers, with this list.

**What it must have:**

- **MySQL 5.7 or 8.** The portal is tested with 5.7.
- **It must be reachable from the computer of each person in the team,** also from outside the office if someone works
  from home or with mobile data. If the server only lets people in from certain networks (that is normal, and safer),
  you have to add each person's networks or use a VPN (a connection that makes your computer be "inside" the office
  network even when you are away).
- **An empty database** for the portal. The portal creates the tables by itself, the first time.
- **A user for the portal** with permissions only on that database: read, save, change and delete data, and create and
  change tables.

**For whoever sets it up,** this is what is needed, in MySQL's language (change the database name, the user name and
the password to your own):

```sql
CREATE DATABASE iso42001 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'portal'@'%' IDENTIFIED BY 'una-contraseña-larga';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES ON iso42001.* TO 'portal'@'%';
```

**What details they must give you** (you will type them in during the installation):

| Detail | What it is | Example |
|---|---|---|
| Server address | Where the MySQL is | `mibase.eu-west-1.rds.amazonaws.com` |
| Port | The "door" you go in through | `3306` (MySQL's usual one) |
| User | The user the portal signs in with | `portal` |
| Password | That user's password | |
| Database | The name of the empty database | `iso42001` |

Where to set it up is up to you: a company server or one in the cloud (Amazon, Google, Microsoft and others rent them
ready-made). It must be switched on whenever someone uses the portal.

## The files folder

In the shared mode, the evidence files (the proof for each requirement) go in a **shared folder**, so that the whole
team sees the same ones. For example:

- a **Teams or SharePoint folder synced with OneDrive** (in Teams: the channel → "Files" → "Open in SharePoint" →
  "Sync");
- a company **network folder**.

**Each person chooses it once on their computer**, during the installation. It must be the same folder for everyone.
Choose the team's general folder for the ISO (for example, "ISO 42001"), not a company's: inside it, the portal creates
a folder for each company. If one day the portal can't find it (it has been moved or has stopped syncing), it asks you
for it again.

**The first time,** the portal creates about 160 folders per company. If it is a synced folder, it is best for just one
person to start it and wait for them to upload before anyone else signs in: if two people create them at the same time,
the sync program may duplicate some.

In the "only on this computer" mode, the files go in the data folder you chose and there is nothing to do.

## Optional: AI (Claude)

The portal can use Claude, Anthropic's AI, to:

- **review files:** say whether what you have uploaded meets a point;
- **suggest** whether each control in the Statement of Applicability applies and write the reason;
- **write drafts** of the documents the standard asks for;
- **prepare the draft of the management review;**
- the **chat** («Preguntar», Ask), to ask about the standard or about the portal.

**What you need:** to have **Claude Code** installed on your computer and to be signed in with your Claude account. The
portal uses your Claude session, that is, your subscription: you don't have to put any key in the portal. Each person in
the team uses their own.

1. Install Claude Code following the instructions on its official page: <https://claude.com/claude-code>.
2. Open it once and sign in with your account.
3. Start the portal again.

**What leaves your computer:** when you use one of these helps, the portal gives Claude what it needs for that task
(for example, the text of the file you are reviewing or the answers to the questionnaire). Nothing else, and only when
you click the button.

**Without Claude:** the AI buttons say it is not available. Everything else works the same.

## Optional: email reminders (Outlook)

The portal can send an email and a Windows notification with what is pending: on the 1st of each month and every
Monday, with the portal closed.

**What you need:** **classic Outlook** (the usual desktop program) installed and with your email account set up. The
"new Outlook" does not work. The email is sent from your account, without typing passwords into the portal.

1. In the portal, **«Ajustes» (Settings) → «Avisos por correo» (Email reminders)**: tick the box, check who it goes to
   and from which account, and save.
2. Double-click, once, **`programar-avisos.bat`** (in the program folder). It creates the Windows task that sends
   them.
3. To check it: **«Mandar un aviso de prueba»** (Send a test reminder), in the same place.

**Without Outlook:** there are no email reminders. The reminders inside the portal («Lo siguiente» (What's next), in
«Inicio» (Home)) work the same.

## Backups

The portal does not make backups by itself. Make them yourself, every so often (for example, once a month and before
updating).

**Only on this computer:**

1. Shut down the portal (close the black window or `parar.bat`).
2. Copy the whole **data folder** (by default, `Documentos\Portal ISO 42001`) somewhere else: an external drive, a
   cloud folder…
3. To restore it: shut down the portal and put the copy back in its place, with the same name.

**Shared with your team:** there are two things to copy.

- **The MySQL:** ask whoever runs it to have automatic backups. Cloud services usually make them by themselves; on your
  own server, your IT person will know how (with MySQL's backup tool).
- **The files folder:** if it is on Teams, SharePoint or a network folder, they usually already keep earlier versions.
  If not, copy it like the one in the "only on this computer" mode.

**Your computer's settings** (the mode, the chosen folder and the MySQL details) don't need copying: if they are lost,
the portal asks again.

## Updating to a new version

To know which version you have, look at the footer of any screen: «Versión del 17/11/2026» (Version of 17/11/2026).

Your data is not in the program folder, so updating means swapping that folder for the new one. `actualizar.bat` does it
for you:

1. **Make a backup** (see above).
2. **Double-click `actualizar.bat`**, in the program folder. It checks on GitHub whether there is a newer version than
   yours:
   - If there is not, it says «Ya estás al día» (You are up to date) and does nothing else.
   - If there is, it says what date it is from and asks whether to update: type `s` and press Enter.
3. **By itself** it shuts down the portal, downloads the new version, swaps the program files and starts the portal
   again. The first start afterwards takes a couple of minutes, as when installing.

It does not touch your data, your settings or the passwords. The previous version is kept aside, next to
the portal settings in your Windows user (folder `version-anterior`), and if something fails halfway, it leaves the program as it was. It only
connects to GitHub to check the version and download it: it sends nothing.

**By hand**, if you prefer (or if that computer has no internet and you bring the ZIP from another one):

1. **Make a backup** (see above).
2. **Shut down the portal** (close the black window or `parar.bat`).
3. **Download the ZIP** of the new version.
4. **Rename the program folder** to "Old portal" and unzip the new one in the same place, with the name the old one
   had. Your data is not in the program folder (it is in the data folder or in the MySQL), so it is not lost. When you
   have checked that the new one works, delete "Old portal".
5. **Double-click `arrancar.bat`.** The first time it takes a couple of minutes, as when installing. It does not ask
   anything again: you sign in with your account and everything is there.

When it starts, the portal updates the database by itself: it adds whatever is missing and deletes nothing.

**In the shared mode, the whole team should update,** each on their own computer. If someone uses an older version than
the others, something new may not work for them.

If you had scheduled the email reminders and you put the program in a different folder, double-click
`programar-avisos.bat` again: the Windows task looks for the program where it used to be.

## If the administrator forgets their password

If someone forgets their password, the administrator gives them a new one from «Administrar». If the one who forgets it
is the administrator, and there is no other administrator to change it:

1. In the program folder, double-click `olvide-contrasena.bat`. A black window opens.
2. Type your email and press Enter.
3. Type the new password and press Enter; then, again. What you type does not show on screen: that is normal.
4. If it says «Contraseña de … cambiada» (Password for … changed), you can now sign in with it. Press a key to close
   the window.

It works with the portal on that computer: the MySQL if it is shared (it must be able to reach it, like the portal), or
its data folder if it is "only on this computer".

Deleting a company is not done from the portal either, because it takes all its data with it. (Renaming it is: in
«Administrar».) It is done with the accounts program, by typing a command: if you are not comfortable with this, ask
your IT person to do it with you. In the program folder, click the address bar (at the top), type `cmd` and press
Enter; in the black window, `.venv\Scripts\python scripts\cuentas.py --help` shows everything it can do.

## If something does not work

**«El portal necesita Python»** (The portal needs Python): install it as explained in
[Download and start](#download-and-start), ticking "Add python.exe to PATH". If you already installed it without
ticking it, open the Python installer again, choose "Modify" and tick it.

**«Ya hay un portal encendido»** (A portal is already running): there is another one open, perhaps in a window you
can't see. Double-click `parar.bat` and start it again.

**The portal does not open because another program is using its "port"** (the door through which the browser talks to
the portal; the portal's is 8000). Pass this on to your IT person: in a `cmd` window in the program folder,
`set PORTAL_PUERTO=8010` and then `arrancar.bat`.

**«Sin conexión»** (No connection) **(shared mode):** the portal can't reach the MySQL. It takes a few seconds to say
so, because it waits for the server to answer. Check, in this order:

1. **That you have internet.**
2. **That the server is switched on:** ask whoever runs it, or a colleague whether it works for them.
3. **That the server lets you in from your network.** This is the most common cause when it works at the office and
   not at home or with mobile data (or the other way round). Pass this on to your IT person: in PowerShell (in the
   Start menu), with your server's address,

   ```
   Test-NetConnection mibase.ejemplo.com -Port 3306
   ```

   If at the end it says `TcpTestSucceeded : False`, it can't be reached from this network. Ask whoever runs the
   server to add your network, or use the company VPN.
4. **That the MySQL details have not changed.** If your team has changed the MySQL password or its address, click
   **«Cambiar los datos del MySQL»** (Change the MySQL details) on the same «Sin conexión» screen, type in the new ones
   and «Guardar y entrar» (Save and sign in). The current ones are already filled in, except the password. Nothing is
   lost: the portal's data is in the MySQL.

**The portal asks for the files folder again:** it can't find the one you chose. It may have been moved, stopped
syncing, or the network drive may not be connected. If it is back, click «Usar esta carpeta» (Use this folder); if
not, choose where it is now.

**The AI buttons say it is not available:** see [Optional: AI (Claude)](#optional-ai-claude).

**The reminder email is not sent:** it is recorded in «Actividad» (Activity) with the reason. Usually there is no
classic Outlook, or the chosen account is not in that Outlook.

## Security

- **The MySQL details give access to everything.** Whoever has them can get into the database directly, without going
  through the portal, and change accounts, passwords or company data. «Administrar» only controls what is done inside
  the portal. Give them only to trusted people in the team, and never through an open channel (an email to many
  people, a public chat).
- **The MySQL should only let people in from your networks** (see [The MySQL: what to ask for](#the-mysql-what-to-ask-for)),
  and with a user that only has permissions on the portal's database.
- **If someone leaves the team,** remove their account in «Administrar». If they had the MySQL details, change the
  password of the MySQL user and type the new one on each computer: when it starts, the portal will say «Sin
  conexión»; click **«Cambiar los datos del MySQL»**, type the new password and **«Guardar y entrar»**. Nothing is
  lost.
- **In the "only on this computer" mode,** the data is in a normal folder on your computer: anyone who signs in with
  your Windows user can see it.
- **The portal can only be seen from your computer:** it is not opened to the network or to the internet.

## Legal notice

Developed at Movired.

The portal has an **internal use license** (PolyForm Internal Use 1.0.0). In short:

- **You may** use it and modify it for your company's internal work; everyone who works there can use it.
- **You may not** give a copy to another company or to anyone outside: whoever wants it should download it from the
  GitHub repository, [github.com/aracilpau/portal-iso42001](https://github.com/aracilpau/portal-iso42001).
- **Nor may you** sell it, offer it as a service to others or install it for a client.

This is a summary: the text that applies is the one in the `LICENSE` file. It can also be seen in the portal, in the
"Licencia de uso interno" (internal use license) link at the bottom of every screen.

- The portal helps you keep your AI management system up to date according to the ISO/IEC 42001 standard, but it
  **does not certify anything** and does not replace the standard, an audit or an expert's advice. The guide it
  includes explains the requirements in its own words; for certification you need the original standard.
- ISO/IEC 42001 is a standard by ISO and IEC. This portal is not related to or endorsed by those organizations.
- What the AI writes are **drafts**: review them before using them.
- It is offered as is, without warranties. Make backups.
- **If you see the portal for sale**, offered as a service or installed for clients, let us know: [pauaracil@mvdataworks.com](mailto:pauaracil@mvdataworks.com).
