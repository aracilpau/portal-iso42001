# ISO/IEC 42001 portal user manual

How to use the portal, screen by screen. The portal's chat («Preguntar», Ask) also uses it to answer questions about
using the portal. How to install it, update it and make backups is in [`install.md`](install.md); the license (internal
use only), in its [legal notice](install.md#legal-notice).

The portal has a single style, **«Plano» (Blueprint)**, with a light and a dark mode: the menu at the top, with the search box
and the «Preguntar» (Ask) button.

**About the language:** the portal's screens are in Spanish. Chrome and Edge can translate them: click the translate
icon in the address bar, or right-click on the page → "Translate to English". Some words may come out odd, because it
is an automatic translation. This manual gives the names on the screen in Spanish, with their meaning, so you can find
them either way.

## Index

- **entrar** — Signing in with email and password, choosing a company, switching company and signing out
- **inicio** — Home: progress, what is left to do and «Ha pasado algo»
- **requisitos** — The list of requirements and its filters
- **revision-direccion** — Preparing the draft of the management review (9.3)
- **ficha** — The page of a requirement: its points, ticking them, due dates, renewing
- **archivos** — Uploading files, removing them, new versions and previous versions
- **revisor** — «Revisar con IA»: the AI says whether the files of a point meet it
- **borradores** — «Hacer borrador»: a Word file with the template of a requirement's document
- **sistemas-en-puntos** — Points that go per AI system and points that are met automatically
- **inventario** — The AI inventory: adding a system, the page of each system, retiring
- **declaracion** — The Statement of Applicability: deciding whether each control applies
- **cuestionario** — «Empresa»: the company questionnaire, all together, and the step-by-step for the first time
- **propuestas** — The AI's proposals for the Statement of Applicability
- **ha-pasado-algo** — «Ha pasado algo» and reopening requirements
- **avisos** — Alerts: overdue, due soon, reminders
- **avisos-correo** — Email alerts and Windows notification: on the 1st and every Monday
- **actividad** — The activity log
- **ajustes** — Settings: what it alerts about, email alerts, reviews, reminders, and theme
- **buscador** — The search box (Ctrl K)
- **chat** — The chat («Preguntar»)
- **carpetas** — The evidence folders on the computer
- **arrancar** — Starting, first-time installation (the two modes), shutting down and the test portal
- **conceptos** — Concepts: met, due, event-driven, supported, recommended, not applicable

---

## entrar

**What it is:** the first thing you see when you open the portal.

- **Signing in:** email and password. If they are wrong, it says so without saying which of the two is wrong.
- **Choosing a company:** only the companies you have been assigned to are shown. If you have none, it says so. Each
  company has everything of its own: tracking, Statement of Applicability, inventory, questionnaire, settings, alerts,
  Activity and files. Nothing is mixed between companies. In some portals there is also **«General»** (General): a
  shared space that all accounts can enter (it is not a company being certified). New installations do not create it.
- **Welcome screen:** when you enter a company (also when changing company) and when you reload the page, a colourful
  welcome screen with «42001» in large type appears and fades away by itself in a moment; a click or a key removes it
  sooner. It does not appear when moving between screens.
- **Where everything is:** in the shared portal, on the server (a MySQL database): the accounts, the companies and what
  you fill in are valid from any computer, and what one person ticks the others see. The evidence files are in the
  shared folder each person chooses on their computer (see «carpetas»). In the «Solo en este ordenador» (Only on this
  computer) mode, everything is on your computer.
- **No connection:** if the portal says «Sin conexión» (No connection), it cannot reach the server where the data is.
  There may be no internet, the server may be off, or it may not allow access from the network you are on (this
  happens when working outside the office or with mobile data). If your team has changed the MySQL password, press
  «Cambiar los datos del MySQL» (Change the MySQL details) and type the new one. If not, tell whoever installed the
  portal; what to check is in [`install.md`](install.md#if-something-does-not-work), "If something does not work". If
  the connection drops while saving something, nothing is saved halfway: do it again.
- **No files folder:** if it has not been chosen on your computer or is no longer there, the portal asks for it when
  you sign in (see «carpetas»).
- **In the header,** top right: the company and your name, **«Cambiar empresa»** (Switch company: back to the list),
  **«Administrar»** (Administer: only the administrator), **«Cambiar contraseña»** (Change password) and **«Salir»**
  (Sign out).
- **Every time the portal is started** you have to sign in again; also when you close the browser.
- **Changing your password:** «Cambiar contraseña», with the current one and the new one twice (at least 8
  characters). If you do not know the current one, ask the administrator to set a new one for you.
- **Administrar** (only administrators see it; the others do not):
  - **Accounts:** create one (name, email, password and which companies it can enter), tick which companies each one
    can enter, change its password (the administrator types it and passes it on), **«Quitar»** (Remove: the person can
    no longer enter, even with the portal open; what they did stays in Activity, and it is undone with «Volver a dejar
    entrar» (Let in again)) and appoint or remove administrators («Hacer administrador» (Make administrator) and
    «Quitar de administrador» (Remove as administrator), with a confirmation that says what changes).
  - **Companies:** the list, create a new one and **«Cambiar nombre»** (Rename: you type the new name and confirm it;
    only the visible name changes: its data and its files folder stay the same, and it is recorded in its Activity).
    Deleting a company is not done from the portal, because it takes all its data with it: this is explained in
    [`install.md`](install.md#if-the-administrator-forgets-their-password), "If the administrator forgets their password".
  - **Removing yourself:** your own row also shows «Quitar de administrador» and «Quitar», with confirmation. If you
    remove yourself as administrator you stop seeing «Administrar»; if you remove your account, you are signed out
    and can no longer enter. To come back, another administrator has to appoint you or let you in.
  - **So you are not locked out:** there must always be one administrator who can sign in. If you are the only one,
    the portal does not let you remove yourself and asks you to appoint someone else first.
  - **Who administers:** at first, the first account created (in a new installation, the one of the person who
    installed the portal). After that, whoever that person appoints.
- **If the administrator forgets their password:** if there is another administrator, they can change it in
  «Administrar». If not, it is done with a program that comes with the portal: this is explained in
  [`install.md`](install.md#if-the-administrator-forgets-their-password), "If the administrator forgets their password". **Anyone with
  the MySQL details can do this with any account:** give them only to people you trust.
- **If you are removed from a company or it is deleted,** you stop seeing it as soon as you move to another page.
- **Who did what:** everything you do is recorded under your name: in Activity, on the requirement page («Marcado el …
  por Ana» (Ticked on … by Ana), and on each file «Subido por Ana» (Uploaded by Ana); if it was added from File
  Explorer, «Añadido en la carpeta» (Added in the folder)) and in «Cambios» (Changes) of the Statement of
  Applicability. What was done before accounts existed has no name. If someone is removed, what they did stays under
  their name.

## inicio

**What it is:** the first page, «Inicio» (Home). It shows how you are doing and what you have pending.

- **Progress:** two percentages, «Obligatorios» (Mandatory: clauses 4 to 10, which always have to be met) and
  «Controles del Anexo A» (Annex A controls: only those that apply). A requirement counts when it is complete.
  Controls not yet decided count as if they applied; those that do not apply do not count. Recommended points do not
  count in the percentage. Controls that are only for the AI you offer to customers, if you have none, are «No hace
  falta por ahora» (Not needed for now) and do not count either (it says so below). The greeting only says «Todo al
  día» (All up to date) if the mandatory requirements are also complete.
- **What is pending:** the list «Lo siguiente» (What's next), sorted by urgency (overdue, due soon, reminders, new
  systems, the question «¿Ha pasado algo?» (Has something happened?)), each with its button: «Ir a renovar» (Go to
  renew), «Hecho» (Done), «Decidir» (Decide), «No, nada» (No, nothing) (see **avisos**). There is also a map with a
  square per requirement, coloured by its status (hover the mouse to see which one it is).
- **«Ha pasado algo»** (Something happened): the five situations one click away (see **ha-pasado-algo**).
- If there are Annex A controls not yet decided, an alert takes you to the Statement of Applicability.
- If something is missing in «Empresa» (Company), another alert takes you to the questionnaire.

## revision-direccion

**What it is:** on Home, next to the progress, the button **«Preparar la revisión del año»** (Prepare the year's
review). Claude writes, with the portal's data, a **draft of the minutes** of the management review (9.3), in Word,
ordered as the standard requires: actions from previous reviews, changes (what was entered in «Ha pasado algo», the
inventory, the Statement of Applicability), performance (progress, due dates, measurements and audit), opportunities
for improvement, and conclusions and decisions.

- **Period:** from the last review uploaded to 9.3 until today; if there is none, the last year. Below the button it
  says which period it covers.
- The figures and facts come from the portal's data. What only management can fill in (date, attendees, conclusions,
  decisions with owner and deadline, resources) is highlighted as **[POR COMPLETAR]** (TO BE COMPLETED).
- It takes about a minute and is downloaded. It is not saved in the portal and does not count as evidence: when
  management approves it, it is uploaded to 9.3, and the next review will start from that day.
- It needs Claude Code on the computer.

## requisitos

**What it is:** the 65 requirements of the standard: 27 mandatory ones (clauses 4 to 10) and 38 Annex A controls.

- Each row: code, title, how it is demonstrated («Documento» (Document), «Registro» (Record), «Inventario»
  (Inventory), «Práctica» (Practice)), how often it is reviewed and the progress («3 de 4» (3 of 4)). Click it to open
  its page.
- Filters with their count: «Todos» (All), «Pendientes» (Pending: those that apply and are not complete), «Vencen o
  vencidos» (Due or overdue), «Completos» (Complete), «No aplican» (Not applicable).
- Hovering the mouse over a requirement shows what it is.

## ficha

**What it is:** the page of a requirement. You get there from the list, the search box or any link to its code.

- **At the top:** the code, the title, what it is in plain words, how it is demonstrated and how often, and its
  percentage («2 de 3 puntos» (2 of 3 points)).
- **The points:** what has to be met. Each one shows its text, its type (Documento, Registro…), **«Te pedirán»** (You
  will be asked for: examples of what the auditor asks for) and whether it is recommended.
- **Ticking a point:** click the **checkbox** to its left. Clicking it again unticks it. Only the requirement's own
  points are ticked by hand; points that are met automatically or go per system have no checkbox (see
  **sistemas-en-puntos**).
- **Due dates:** when you tick a point, it says «Vence el …» (Due on …) (one year later, or whatever the general
  review says). Before it is due it changes to «Vence pronto» (Due soon); when it is due, «Vencido: ya no cuenta hasta
  que se renueve» (Overdue: no longer counts until renewed). Event-driven requirements do not fall due by date: they
  say «No vence por fecha» (Not due by date).
- **Renewing:** the point's «Renovar» (Renew) button says it is still valid and starts counting again from today. It
  stands out when the point is due soon or overdue.
- **«Vuestras notas»** (Your notes): what is specific to the company (who is in charge, where you keep each thing, how
  you do it). It saves itself as you type and every account of the company sees it. It is in the right-hand column.
- **«¿Ha cambiado algo?»** (Has anything changed?): in requirements that are reopened by an event and have something
  ticked. It asks for confirmation and sets their points back to pending until you confirm they are still valid (files
  are not deleted). It is a box on the right, with the button «Volver a revisar» (Review again).
- **Annex A controls:** the page says whether it applies to your company and links to the Statement of
  Applicability. If it does not apply, nothing is ticked and its files are not shown.
- **«Lo último»** (Latest): on the right, the most recent things done in that requirement.

## archivos

**What it is:** the evidence for each point (documents, records, screenshots…).

- **Uploading:** drag one or more files **onto the point** (or onto a system's line) and drop them. Also with
  «+ Archivo» (+ File). They are saved in that point's folder (see **carpetas**).
- **Opening:** click its name. PDFs and images are shown in the browser; the rest are downloaded.
- **Removing («Quitar»):** moves the file to the requirement's «Versiones anteriores» (Previous versions), with the
  point and the date in front. It is not deleted.
- **«Subir versión nueva»** (Upload new version): the point's current files move to previous versions and the new one
  comes in. If the point was ticked and has a due date, it is also renewed from today.
- **Previous versions:** at the end of the page. From there a file can be **deleted forever** (it asks for
  confirmation; it cannot be undone).
- Key difference: **renewing** says that what is there is still valid (it does not change files); **uploading a new
  version** replaces the files and, if the point has a due date, also renews it.

## revisor

**What it is:** on each point that has files (and on each system line), the button **«Revisar con IA»** (Review with
AI). Claude reads the files of that point, all together, and says whether they meet it: **SÍ** (YES, in green), **NO**
(NO, with what is missing, in orange) or **NO SE PUEDE SABER** (CANNOT TELL, in grey), with the reason and, under «Ver
detalle» (See detail), which part of the file it relies on. If the file has nothing to do with the point, it is a
**NO**: it says so and explains which document should be uploaded. **NO SE PUEDE SABER** is for files that cannot be
read and for what is not demonstrated with documents.

- It compares against what the point requires and its «Te pedirán», and against the company questionnaire.
- It reads Word, Excel, PDF, images and text. In a PDF it also sees who signed it digitally and when (the name and the
  date, without the ID number), but it does not check that the signature is valid: that is why it shows «Firma sin
  comprobar» (Signature not checked), and you have to open it in Adobe before ticking the checkbox. A scanned PDF with
  no text cannot be read. If the files are very long, it says so instead of reviewing them halfway.
- It takes about a minute. **It does not tick anything:** you decide on the checkbox.
- The answer stays saved. If the point's files change afterwards (one is uploaded, removed or replaced), a warning says
  that **it is from a previous version**, and the SÍ or NO is shown without its colour: it is worth pressing «Volver a
  revisar» (Review again).
- It is recorded in Activity as «revisado por la IA» (reviewed by the AI). The files go to Claude using the session of
  the person using the portal.
- It needs Claude Code on the computer.

## borradores

**What it is:** on the page of requirements that call for writing a document, the button **«Hacer borrador»** (Make
draft) downloads a Word file with the document written by the AI for the company. It is a box on the right.
It may take a minute.

- There are nine templates: context and interested parties (4.1 and 4.2), AI policy (5.2 and A.2.2), scope (4.3),
  roles and responsibilities (5.3 and A.3.2), risk and impact procedure (6.1.2 and 6.1.4), objectives (6.2), control of
  documented information (7.5), internal audit programme (9.2) and nonconformities (10.2).
- **Starting point:** the other 28 requirements that call for a document of their own (for example 7.4 or many Annex A
  controls) have a generic template: a section for each point demonstrated with a document, with what it has to say
  and what the auditor will ask for, all as [POR COMPLETAR], and at the end what does not go in the document. The only
  company details it includes are the name, the date and who approves.
- There is no button on requirements that are only demonstrated with records or in practice (for example 7.3), nor on
  those met through others (8.1).
- **With AI:** Claude writes the document in a formal style with everything in «Empresa» (including the open questions
  and the AI's questions already answered), the inventory with the page of each system and «Vuestras notas» (Your
  notes). **It does not read the uploaded files.** At the top it says «Borrador hecho con IA. Revísalo y apruébalo antes
  de usarlo» (Draft made with AI. Review and approve it before using it).
- **Fixed structure:** the headings and sections are always those of the template (or of the generic starting point),
  in the same order; the AI only writes inside them. If nothing it is given has changed, you get the same draft as
  last time, without asking the AI again.
- **What is still needed:** at the end of the draft, the questions the AI needs to complete it. They also appear at
  the end of «Empresa», under «Lo que pregunta la IA» (What the AI asks); what is answered there is used by all later
  drafts. It only asks what is not already in the questionnaire or the inventory: anything missing from those is
  answered in its own place.
- What the AI does not know, or what the company says it does not have, appears as **[POR COMPLETAR]**: the document
  does not describe the gap, and when reviewed with the AI it shows up as what is missing. If it mentions another
  company document, such as the AI policy, it warns with **[A CONFIRMAR]** (TO BE CONFIRMED) that you have to check it
  is uploaded and fits: the AI has not read it. And what it proposes but someone has to check (the laws that apply)
  appears as **[A CONFIRMAR]**; both in yellow.
- **Without AI:** if Claude is not on the computer, fails or does not respect the structure, you get the filled-in
  template as before, with the notice «Hecho sin IA» (Made without AI) and the reason. That one is filled in with the
  general details, the «Sí / No» (Yes / No) answers and the systems in the inventory: it shows the company name, its
  systems and only the sections that apply to it; with «No lo sé» (I don't know), the section appears with a warning to
  confirm it.
- In Activity: «borrador del documento hecho con IA» (document draft made with AI) or «descargado (sin IA)»
  (downloaded, without AI).
- If something is missing in «Empresa», above the button it says how many questions are still to be clarified
  (unanswered or set to «No lo sé»), with a link to answer them.
- What only the company can decide (owners, risk it accepts, where it is published, the signature…) is highlighted in
  yellow as **[POR COMPLETAR]**.
- It is not saved in the portal and does not count as evidence: it is completed, approved and uploaded. **Below the
  button it says which points to upload it to** (including those of other requirements that use the same document,
  such as 4.1 and 4.2), which ones also once signed (the policy, to 5.2.e) and which points of the requirement it does
  not cover, with what is needed for each one.
- The templates are the same for any company and are in `guia/plantillas/`.

## sistemas-en-puntos

- **Points per system:** some points are met once for each AI system in the inventory (for example, the AI system
  impact assessment). They have one line per system, each with its checkbox, its files and its due date. The point is
  met when it is met for all the active systems it applies to. Some are «Solo la IA que ofrecéis a clientes» (Only
  the AI you offer to customers) and ask nothing of the AI the team uses. If you have no AI that you offer to
  customers, those points are «No hace falta por ahora» (Not needed for now): they count neither as done nor as
  pending, and if all the points of a requirement are like that, the requirement does not count in the percentage
  either. When you add one, they become pending again.
- **Points that are met automatically («apoyados», supported):** they rely on other requirements and are ticked
  automatically when those are complete. They have no checkbox; they say «Se marca solo cuando completes …» (It is
  ticked automatically when you complete …), with the requirement's name.
- **Points from the system page:** A.4.2.a to A.4.6.a are met automatically when the matching field is filled in on
  the page of each system in the inventory.
- With no systems in the inventory, points per system stay pending.

## inventario

**What it is:** every AI in the company: the one you offer to your customers and the tools the team uses (ChatGPT,
Copilot…).

- **Adding a system:** type the name, choose what type of AI it is («La ofrecemos a clientes», We offer it to
  customers, or «La usa el equipo», The team uses it) and press «Añadir» (Add). Its page opens.
  - When a system is added (or activated again), the page asks whether to reopen risks (8.2, 8.3) and suppliers
    (A.10.3), which cover the whole company. You can reopen what is ticked or answer «No hace falta» (Not needed). If it
    is not answered, the question stays pending in the alerts.
- **The page of each system:** five fields (what it is for, data, tools, infrastructure, people), each with its help.
  It saves itself when you leave each field. Each filled section counts for its requirement (A.4.2 to A.4.6): nothing
  else needs uploading for that.
- **Retiring:** the system stops counting; its page is kept and its files move to previous versions. It can be
  **activated again** («volver a activar») from the list of retired systems.

## declaracion

**What it is:** the Statement of Applicability: for each of the 38 Annex A controls, whether it applies to the company
and why. The auditor asks about both cases.

- **Deciding a control:** choose «Aplica» (Applies) or «No aplica» (Does not apply) and write the reason. It saves
  itself when you stop typing (a second and a half) or when you leave the box.
- **Changing a decision:** when switching from applies to does not apply (or the other way round), the previous reason
  is cleared and a warning asks for the new one; that reason is kept as the reason for the change in «Cambios».
- **Tabs:** «Controles» (Controls: deciding), «Cambios» (each decision and change with date and reason) and
  «Documento» (Document: preview; downloaded in Word or PDF, or saved as evidence in 6.1.3.c).
- While a control is undecided, it counts as pending in the progress.
- **Unticking:** clicking the chosen option again («Aplica» or «No aplica») unticks it and the control goes back to
  «Sin decidir» (Undecided). It is recorded in «Cambios» («Se deja sin decidir» (Left undecided)) and in «Actividad»
  (Activity); the reason already written stays in the box.
- When you decide a control does not apply, its evidence folder is renamed «… (no aplica)» (… (not applicable)).
- At the top, how many «Empresa» questions are still to be clarified (they decide many controls), and the AI's
  **proposals**.

## cuestionario

**What it is:** the **«Empresa»** page, in the top menu. What the company is like and how it uses AI, all together:

- **«Datos generales»** (General details): name, what it does, size and who approves.
- **«Cómo es vuestra IA»** (What your AI is like): 10 questions («Sí» / «No» / «No lo sé») that decide which controls
  of the Statement of Applicability apply. Question 1 (do you develop AI?) and question 8 (do you use suppliers?) come
  already answered if the inventory already says so.
- **Open questions,** in 5 blocks (the company and AI; people; customers, laws and suppliers; how you work; if you
  develop AI). They are answered in plain words, as you would to a colleague; each one has an example. Block 5 only
  appears if «No» has not been answered to whether you develop AI. Laws are not asked about.
- Each answer saves itself when changed (the open ones, when you leave the box). At the top it says how many
  questions are answered: «No lo sé» counts as unanswered, just like a blank one.
- **When you change an answer that already had something,** below it appears the list of requirements that depend on
  it, as in «Ha pasado algo», to reopen those that need it. It does not appear when answering for the first time.
  General details do not reopen anything. Changing an answer does not touch what has already been decided in the
  Statement of Applicability.
- **The step-by-step:** the first time someone enters a company whose questionnaire has not been started, it appears
  step by step (details, Yes/No and one block of open questions per step), with «Siguiente» (Next: saves), «Saltar
  este paso» (Skip this step) and «Saltar el cuestionario» (Skip the questionnaire). Once finished or skipped, it does
  not appear again; everything can be changed later in «Empresa».
- It is used by the AI's proposals, the document drafts and the chat (the open questions, for now, only by the chat:
  the drafts will use them when the AI writes them). While something is unanswered or set to «No lo sé», Home and the
  «Hacer borrador» button say how many questions are still to be clarified.

## propuestas

**What it is:** the «Proponer qué controles aplican» (Propose which controls apply) button, below the questionnaire. For each control it proposes «APLICA»
(APPLIES), «NO APLICA» (DOES NOT APPLY) or «FALTA SABER» (NEED TO KNOW), with the reason. It takes about half a minute.

- **Who decides each one (mixed Statement of Applicability):**
  - **«Según tu respuesta a la pregunta N»** (According to your answer to question N): decided by the portal, always
    the same way. «Sí» → applies; «No» → does not apply. If a control depends on two questions, it applies if either
    one is «Sí».
  - **«Aplica casi siempre»** (Applies almost always): the controls that apply to almost any company.
  - **«Propuesta de la IA»** (AI proposal): the unclear ones (question set to «No lo sé» or unanswered, with systems in
    the inventory that can clarify it). Claude decides them and says what it relies on.
  - With the question set to «No lo sé» or unanswered and an **empty inventory**, FALTA SABER appears with the question.
- Claude writes the reason for all of them, including those decided by the portal, but it cannot change the portal's
  decision.
- **«Míralo:»** (Take a look:) appears if something does not add up: for example, the inventory contradicts an answer,
  or the AI would have said something different from the portal. The decision does not change; it is for you to check.

- On each control: **«Aceptar»** (Accept: saves it as the decision), **«Cambiar»** (Change: moves it to the form so
  you can adjust it) or **«Descartar»** (Discard).
- **FALTA SABER:** comes with a question and a box to answer it; when you answer, Claude proposes that control again.
- **«Aceptar todas»** (Accept all): accepts those for undecided controls (not the FALTA SABER ones).
- On controls already decided it only warns if it would propose something else («La IA propondría otra cosa» (The AI
  would propose something else) or «Se propondría otra cosa» (Something else would be proposed)).
- Nothing changes in the Statement of Applicability until it is accepted.
- **Without Claude Code** (or if it does not answer properly), the button still proposes the ones decided by the
  portal; the unclear ones stay as they were until Claude is available.

## ha-pasado-algo

**What it is:** some requirements do not fall due by date (the event-driven ones): you have to go back to them when
something happens.

- You choose the situation: new person or change of role, new AI supplier, incident or complaint, change in the company
  or in its management, or an external change (laws, customers, technology).
- The list of requirements involved appears, with a checkbox on those that have something to review again. «Volver a
  revisar los marcados» (Review the ticked ones again) sets their points back to pending until you confirm they are
  still valid; nothing is deleted. It is recorded in Activity, even if nothing is
  reopened.
- Every so often (by default 4 months) the portal asks «¿Ha pasado algo?» in the alerts. This is changed in «Ajustes»
  (Settings).
- A new AI system does not go here: the inventory asks about it when it is added.

## avisos

**What it is:** what needs attention: overdue points, points due soon, reminders that are due, the question «¿Ha
pasado algo?» and new systems with the reopening question unanswered.

- They are in the «Lo siguiente» list on Home (there is no separate window).
- What it alerts about is chosen in Settings. Reminders are marked «Hecho».

## avisos-correo

**What it is:** an email and a Windows notification with what is pending, without having to open the portal.

- **When it arrives:** on the **1st of each month**, the month's summary (the same as the portal's alerts; if there is
  nothing, «Todo al día» (All up to date)). **Every Monday**, what is already overdue and what falls due that week,
  Monday to Sunday (if there is nothing, «Esta semana no vence nada» (Nothing falls due this week)). If the 1st is a
  Monday, only one email. At 9:00 or, if the computer was off, when it is switched on; if it is not switched on on a
  Monday, it arrives the next day.
- **It works with the portal closed:** a Windows task sends it. The computer just needs to be switched on.
- **Sent from:** the **classic Outlook** on that computer, with the chosen account (no passwords). The "new Outlook"
  does not work. Recipients receive it as an email from whoever has the portal.
- **What it contains:** only codes, requirement titles, points and dates. Never files, their content or system names.
- **The notification:** the box at the bottom right. Clicking it opens Home; if the portal was off, it starts it (in a
  minimised window; it is shut down by closing that window or with `parar.bat`).
- **Who receives it:** the company's users, each with their checkbox in Settings → «Avisos por correo» (Email reminders);
  they are all ticked (including those added later) and whoever does not want them unticks themselves. You can also
  type other email addresses, of people who do not use the portal.
- **Setting it up, once:** in Settings → «Avisos por correo», tick the checkbox, check who receives it and from which
  account, and press «Guardar» (Save). Then double-click `programar-avisos.bat` (in the portal folder). To check it,
  «Mandar un aviso de prueba» (Send a test alert): it is sent straight away and does not count as the 1st-of-month or
  the Monday one.
- **They are off by default:** whoever downloads the portal does not have their email connected to anything until
  they activate them. Each company has its own, and the subject says which company it is from («[Portal ISO 42001 ·
  Mi empresa]»).
- **If the email is not sent** (Outlook is not there, the account does not exist…), it is recorded in Activity with
  the reason and a notification says so.
- **Several computers with the alerts scheduled:** the first one to get there sends the alert and records it on the
  server; the others see it has already gone out and do not repeat it. That is why it may come from one person's
  account or another's.
- **Turning them off:** untick the checkbox in Settings. To also delete the Windows task: Task Scheduler →
  «Portal ISO 42001 - avisos» → Delete.

## actividad

**What it is:** the log of everything done in the portal (ticking, renewing, uploading, removing, deciding, retiring a
system, the questionnaire, the proposals…), with date, time and who did it, most recent at the top. It can be filtered
by requirement and by person. Alerts sent only by the Windows task appear as «el portal» (the portal).
What is put directly into the folders from File Explorer does not appear here.

## ajustes

- **«Qué avisa»** (What it alerts about): overdue, due soon, reminders.
- **«Avisos por correo»:** turning them on, who receives them, from which Outlook account and «Mandar un aviso de
  prueba» (see avisos-correo).
- **How often it asks whether something has happened:** every 4 months by default; it can be turned off.
- **«Revisión general»** (General review): how often points fall due (every year by default, before the annual audit).
- **«Aspecto»** (Appearance): the theme («Automático» (Automatic, follows Windows), «Claro» (Light), «Oscuro» (Dark)).
  It is remembered on that computer.
- **«Opciones avanzadas»** (Advanced options): how many days before it alerts «vence pronto», the list of met points
  with when each one falls due (for reference only: the date is not changed by hand, it is calculated from when it was
  met or renewed), and for each requirement whether it falls due or not and its reminder.
- If there are changes from the recommended settings, «Volver a los valores recomendados» (Back to recommended
  values).

## buscador

The box at the top or **Ctrl K** from any page. Type a code («7.2», «A.10») or words («riesgos» (risks), «proveedor»
(supplier)), without worrying about accents or capitals. Arrows to choose, Enter to go, Esc to close. It searches
requirements and points (not files).

## chat

The **«Preguntar»** button, in the top bar, opens a panel to ask about the standard or about the portal. It knows which
page you are on. It only looks things up: it never ticks, uploads or decides. Conversations are not kept when the
portal is closed. It needs Claude Code on the computer.

## carpetas

- In the real portal, the evidence is in the **shared folder each computer chooses**, with a folder inside for each
  company: `<carpeta>\<empresa>\pruebas\<requisito>\<punto>\` (for example `…\mi-empresa\pruebas\5.2\5.2.a\`).
  It can be, for example, a Teams or SharePoint folder synced with OneDrive: what you upload, OneDrive takes to Teams
  and to the others' computers, and the other way round. In the local mode, in the portal folder: `datos\<empresa>\pruebas\…`.
  For points per system, one subfolder per system. Previous versions are in `<requisito>\historial\`.
- **Choosing the folder, once per computer:** when you sign in, before choosing a company, the portal asks «¿Dónde se
  guardan los archivos de pruebas?» (Where are the evidence files kept?). **«Examinar…»** (Browse…) opens the Windows
  window to choose it (or you paste its path) and **«Usar esta carpeta»** (Use this folder) records it. It is valid for
  all companies: you choose the top one, the one that has a folder for each company inside it (for example, `empresa-a` and
  `empresa-b`), not a single company's folder; if you choose one of those, the portal says so. It has to be the same
  on all computers. It is saved in your Windows user settings (`AppData`), not in the program folder: when the portal
  is updated it does not ask again. If one day the folder is not there (it was moved or stopped syncing), it says so
  and asks for it again.
- **Syncing a Teams folder, once per computer:** in Teams, the channel → «Compartido» (Shared) tab (or
  «Archivos» (Files)) → «Abrir en SharePoint» (Open in SharePoint) → «Sincronizar» (Sync), and accept opening OneDrive
  (if it offers to back up the Desktop or Documents, «Omitir» (Skip)). Then choose it in the portal.
- **The "review of a previous version" warning** looks at the name and size of the files, not the date: OneDrive
  sometimes changes the date without anyone touching the file.
- **The first time,** the portal creates about 160 folders per company: it is best for a single person to start it and
  to wait for OneDrive to upload them before someone else opens it (if two people create them at the same time,
  OneDrive may duplicate some).
- In File Explorer and in Teams you see the folders of **all** the companies in the channel, even though in the portal
  each person only sees their own.
- **The folder rules:** what is put in from File Explorer also appears in the portal.
- The folder of a control that does not apply is called «… (no aplica)».
- None of this is uploaded to git: it is company data.

## arrancar

- **`arrancar.bat`** (double-click): starts the portal and opens it in the browser (http://localhost:8000). Closing its
  black window shuts it down. It needs Python; if it is not there, it says so and opens the download page.
- **The first time (the installation):** the portal explains the two modes and you choose one:
  - **«Solo en este ordenador»:** nothing else to install. You choose where the data goes (by default,
    `Documentos\Portal ISO 42001`), the account and the first company are created, and you go in.
  - **«Compartido con mi equipo»** (Shared with my team): the data in a MySQL database and the files in a shared
    folder. You type the MySQL details (**«Probar conexión»** (Test connection) says whether they work), choose the
    folder (see «carpetas») and, if you are the first, the account and the first company are created. If the MySQL
    already has accounts, you join a team that already exists: nothing is created and you sign in with the account
    made for you by whoever administers it.
- **What you choose is saved in your Windows user** (`AppData\Roaming\Portal ISO 42001`: `ajustes.json` and, in the
  shared mode, `secretos.env` with the MySQL details), outside the program folder: when the portal is updated it does
  not ask again. Older portals (with `secretos.env` in the program folder) are recognised automatically and work as
  always.
- **`arrancar-local.bat`**: the **local** portal, everything on your computer (`datos` folder), without the server or
  internet (http://localhost:8002), with «LOCAL» in the header. It can be running at the same time as the real one.
- **`parar.bat`**: shuts down the portal, the test one and the local one, even if their windows are not visible.
- **`arrancar-prueba.bat`**: a separate portal with made-up data (http://localhost:8001, `datos-prueba` folder), with
  «PRUEBA» (TEST) in the header. It asks whether to start from scratch. It does not touch the real data. You sign in
  with `prueba@ejemplo.com` and the password `prueba`; to create more accounts or companies in it,
  `scripts\cuentas.py --prueba`.
- **Importing someone else's portal** (their `portal.db` and their evidence folder, even from an older version):
  `python scripts\importar.py PORTAL.DB CARPETA "EMPRESA" --quien "NOMBRE"`. The company must exist and be empty; it
  goes to the MySQL and to the files folder chosen on your computer (with `--local`, to the local portal). Whatever does
  not say who did it is recorded under NOMBRE. The original is not touched.

## conceptos

- **Met («cumplido»):** a point that is ticked (or met automatically) and not overdue.
- **Complete («completo»):** a requirement with all its mandatory points met.
- **Due / due soon / overdue («vence» / «vence pronto» / «vencido»):** when something has to be reviewed again; an
  overdue point no longer counts.
- **Event-driven («por evento»):** does not fall due by date; it is reopened when something happens.
- **Supported («apoyado»):** met automatically when other requirements are completed.
- **Recommended («recomendado»):** good practice, not required; it does not count in the percentage.
- **Not applicable («no aplica»):** an Annex A control the company excludes, with its reason, in the Statement of
  Applicability.
- **Reminder («recordatorio»):** an interim alert to keep doing something during the year; it does not change the
  status of anything.
