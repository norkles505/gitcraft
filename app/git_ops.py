"""Operaciones de git para GitCraft. Usa el binario `git` del sistema."""

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass
class Result:
    ok: bool
    output: str


@dataclass
class Remote:
    name: str
    fetch_url: str = ""
    push_url: str = ""


@dataclass
class RepoStatus:
    is_repo: bool = False
    branch: str = ""
    remote: str = ""
    changes: int = 0
    has_upstream: bool = False
    ahead: int = 0
    behind: int = 0
    fetch_error: str = ""
    error: str = ""
    remotes: list[Remote] = field(default_factory=list)


def _git(path: str, *args: str, timeout: int = 120) -> Result:
    """Ejecuta `git <args>` dentro de `path` sin pedir credenciales por terminal."""
    if not Path(path).is_dir():
        return Result(False, "La carpeta no existe.")
    # Mensajes de git en inglés siempre, para poder reconocer los errores típicos.
    env = {k: v for k, v in os.environ.items() if k != "LC_ALL"}
    env.update({"GIT_TERMINAL_PROMPT": "0", "LC_MESSAGES": "C", "LANGUAGE": "C"})
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except FileNotFoundError:
        return Result(False, "No se encontró git en el sistema. Instálalo para continuar.")
    except subprocess.TimeoutExpired:
        return Result(False, "La operación tardó demasiado y se canceló.")
    output = "\n".join(p for p in (proc.stdout.strip(), proc.stderr.strip()) if p)
    return Result(proc.returncode == 0, output)


def _explain_failure(output: str) -> str:
    """Agrega una pista útil cuando el error de git es de los típicos."""
    low = output.lower()
    hints = []
    if any(k in low for k in ("authentication failed", "could not read username", "permission denied")):
        hints.append("Parece un problema de credenciales. Inicia sesión con `gh auth login` o configura tu token.")
    if any(k in low for k in ("fast-forward", "diverg", "would be overwritten", "non-fast-forward", "rejected")):
        hints.append("Las ramas divergieron o hay cambios en conflicto. Resuélvelo desde la terminal.")
    if any(k in low for k in ("please tell me who you are", "unable to auto-detect email", "empty ident")):
        hints.append(
            "Git no sabe quién eres. Configúralo una vez en la terminal:\n"
            '  git config --global user.name "Tu Nombre"\n'
            '  git config --global user.email "tu@correo.com"'
        )
    return output + ("\n\n" + "\n".join(hints) if hints else "")


def list_remotes(path: str) -> list[Remote]:
    """Equivalente a `git remote -v`: nombre y URLs de cada remoto."""
    res = _git(path, "remote", "-v")
    if not res.ok:
        return []
    remotes: dict[str, Remote] = {}
    for line in res.output.splitlines():
        name, _, rest = line.partition("\t")
        url, _, kind = rest.rpartition(" (")
        kind = kind.rstrip(")")
        if not name or not url:
            continue
        remote = remotes.setdefault(name, Remote(name))
        if kind == "fetch":
            remote.fetch_url = url
        elif kind == "push":
            remote.push_url = url
    return sorted(remotes.values(), key=lambda r: (r.name != "origin", r.name))


def set_remote(path: str, url: str, name: str = "origin") -> Result:
    """Vincula el repo a `url`: agrega el remoto o cambia su URL si ya existe."""
    url = url.strip()
    if not url or url.startswith("-"):
        return Result(False, "Escribe una URL válida del repositorio remoto.")
    exists = any(r.name == name for r in list_remotes(path))
    args = ("remote", "set-url", name, url) if exists else ("remote", "add", name, url)
    res = _git(path, *args)
    if not res.ok:
        return Result(False, res.output)
    verb = "actualizado" if exists else "vinculado"
    return Result(True, f"Remoto '{name}' {verb}: {url}")


def remove_remote(path: str, name: str) -> Result:
    """Quita el vínculo con un remoto (no borra archivos ni commits locales)."""
    res = _git(path, "remote", "remove", name)
    if not res.ok:
        return Result(False, res.output)
    return Result(True, f"Remoto '{name}' desvinculado. Tus archivos y commits locales siguen intactos.")


def get_status(path: str, fetch: bool = True) -> RepoStatus:
    st = RepoStatus()
    if not Path(path).is_dir():
        st.error = "La carpeta no existe."
        return st

    probe = _git(path, "rev-parse", "--is-inside-work-tree")
    if not (probe.ok and probe.output.strip() == "true"):
        missing_git = probe.output.startswith("No se encontró git")
        st.error = probe.output if missing_git else "La carpeta no es un repositorio git."
        return st
    st.is_repo = True

    branch = _git(path, "symbolic-ref", "--short", "HEAD")
    st.branch = branch.output.strip() if branch.ok else ""

    remote = _git(path, "remote", "get-url", "origin")
    st.remote = remote.output.strip() if remote.ok else ""
    st.remotes = list_remotes(path)

    changes = _git(path, "status", "--porcelain")
    if changes.ok:
        st.changes = len([line for line in changes.output.splitlines() if line.strip()])

    if fetch and st.remote:
        fetched = _git(path, "fetch", "--quiet", timeout=60)
        if not fetched.ok:
            st.fetch_error = _explain_failure(fetched.output)

    upstream = _git(path, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if upstream.ok:
        st.has_upstream = True
        counts = _git(path, "rev-list", "--left-right", "--count", "HEAD...@{u}")
        parts = counts.output.split()
        if counts.ok and len(parts) == 2:
            st.ahead, st.behind = int(parts[0]), int(parts[1])
    return st


def pull(path: str) -> Result:
    """Baja los cambios del remoto (solo avance rápido, para no dejar merges a medias)."""
    st = get_status(path, fetch=False)
    if not st.is_repo:
        return Result(False, st.error)
    if not st.remote:
        return Result(False, "Este repositorio no tiene remoto 'origin'.")
    if not st.has_upstream:
        return Result(
            False,
            "La rama no sigue ninguna rama remota todavía. Usa 'Subir cambios' primero.",
        )
    res = _git(path, "pull", "--ff-only")
    if not res.ok:
        return Result(False, _explain_failure(res.output))
    return Result(True, res.output or "Listo.")


def commit_and_push(path: str, message: str) -> Result:
    """Hace add + commit (si hay cambios) y luego push."""
    st = get_status(path, fetch=False)
    if not st.is_repo:
        return Result(False, st.error)
    if not st.branch:
        return Result(False, "No estás en ninguna rama (HEAD desacoplado). Cambia a una rama primero.")

    log: list[str] = []
    if st.changes:
        if not message.strip():
            return Result(False, "Escribe un mensaje de commit.")
        note = ensure_identity(path)
        if note:
            log.append(note)
        steps = (
            ("git add -A", ("add", "-A")),
            ("git commit", ("commit", "-m", message.strip())),
        )
        for label, args in steps:
            res = _git(path, *args)
            log.append(f"$ {label}\n{res.output}".rstrip())
            if not res.ok:
                return Result(False, "\n\n".join(log))
    elif st.has_upstream and st.ahead == 0:
        return Result(True, "No hay nada que subir: todo está al día.")

    if not st.remote:
        log.append("Este repositorio no tiene remoto 'origin'. Agrégalo con:\ngit remote add origin <url>")
        return Result(False, "\n\n".join(log))

    push_args = ("push",) if st.has_upstream else ("push", "-u", "origin", st.branch)
    res = _git(path, *push_args)
    output = res.output if res.ok else _explain_failure(res.output)
    log.append(f"$ git {' '.join(push_args)}\n{output}".rstrip())
    return Result(res.ok, "\n\n".join(log))


# ---------- crear repositorio en GitHub ----------
LICENSE_KEYS = {"MIT": "mit", "Apache 2.0": "apache-2.0", "GPL v3": "gpl-3.0"}
NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def _gh(path: str, *args: str, timeout: int = 120) -> Result:
    """Ejecuta `gh <args>` dentro de `path` sin preguntas interactivas."""
    gh = shutil.which("gh")
    if not gh:
        return Result(False, "No se encontró GitHub CLI (gh). Instálalo desde Ajustes.")
    env = {**os.environ, "GH_PROMPT_DISABLED": "1", "GH_NO_UPDATE_NOTIFIER": "1", "NO_COLOR": "1"}
    try:
        proc = subprocess.run(
            [gh, *args], cwd=path, capture_output=True, text=True, timeout=timeout, env=env
        )
    except subprocess.TimeoutExpired:
        return Result(False, "La operación tardó demasiado y se canceló.")
    stdout, stderr = proc.stdout.strip(), proc.stderr.strip()
    if proc.returncode == 0:
        return Result(True, stdout or stderr)
    return Result(False, "\n".join(p for p in (stdout, stderr) if p))


def ensure_identity(path: str) -> str:
    """Si git no sabe quién eres, configura nombre y correo SOLO en este repo usando tu cuenta de GitHub.

    Usa el correo privado de GitHub (id+usuario@users.noreply.github.com). Devuelve una línea
    para el registro si cambió algo, o "" si ya había identidad o no se pudo obtener.
    """
    has_name = _git(path, "config", "user.name").output.strip()
    has_email = _git(path, "config", "user.email").output.strip()
    if has_name and has_email:
        return ""
    res = _gh(path, "api", "user", "--jq", '[.login, (.id|tostring), (.name // "")] | join("\\t")')
    if not res.ok:
        return ""
    parts = res.output.split("\t")
    if len(parts) < 2:
        return ""
    login, user_id = parts[0].strip(), parts[1].strip()
    display = (parts[2].strip() if len(parts) > 2 else "") or login
    name = has_name or display
    email = has_email or f"{user_id}+{login}@users.noreply.github.com"
    if not (_git(path, "config", "user.name", name).ok and _git(path, "config", "user.email", email).ok):
        return ""
    return f"Git no tenía identidad: se configuró en este repo como {name} <{email}>."


def create_repo(
    path: str,
    name: str,
    description: str,
    private: bool,
    gitignore: str,
    license_name: str,
    readme: bool,
    push: bool,
) -> Result:
    """Crea el repo en GitHub a partir de `path` y, si `push`, hace el primer commit y push."""
    name = name.strip()
    description = description.strip()
    if not NAME_RE.match(name) or name in (".", ".."):
        return Result(False, "El nombre solo puede tener letras, números, guiones, puntos y guiones bajos.")
    if not path.strip():
        return Result(False, "Elige la carpeta local.")
    if not _gh(str(Path.home()), "auth", "status").ok:
        return Result(False, "No has iniciado sesión en GitHub. Hazlo en Ajustes y vuelve a intentarlo.")

    folder = Path(path).expanduser()
    if folder.is_file():
        return Result(False, "La ruta elegida es un archivo, no una carpeta.")
    folder.mkdir(parents=True, exist_ok=True)
    path = str(folder)
    log: list[str] = []

    # --- repositorio local ---
    top = _git(path, "rev-parse", "--show-toplevel")
    if top.ok:
        if Path(top.output.strip()).resolve() != folder.resolve():
            return Result(
                False, f"Esta carpeta está dentro de otro repositorio git ({top.output.strip()}). Elige la raíz."
            )
        remotes = list_remotes(path)
        if remotes:
            return Result(
                False,
                f"Esta carpeta ya tiene un remoto vinculado ({remotes[0].name} → {remotes[0].fetch_url}). "
                "Desvincúlalo en Sincronizar si quieres crear uno nuevo.",
            )
    else:
        init = _git(path, "init", "-b", "main")
        if not init.ok:
            init = _git(path, "init")
        if not init.ok:
            return Result(False, init.output)
        log.append("Repositorio git inicializado.")

    # --- archivos iniciales (nunca se sobrescribe algo que ya exista) ---
    if readme and not (folder / "README.md").exists():
        text = f"# {name}\n" + (f"\n{description}\n" if description else "")
        (folder / "README.md").write_text(text, encoding="utf-8")
        log.append("README.md creado.")

    if gitignore != "Ninguno" and not (folder / ".gitignore").exists():
        res = _gh(path, "api", f"gitignore/templates/{gitignore}", "--jq", ".source")
        if res.ok:
            (folder / ".gitignore").write_text(res.output + "\n", encoding="utf-8")
            log.append(f".gitignore de {gitignore} creado.")
        else:
            log.append(f"No se pudo descargar el .gitignore de {gitignore}: {res.output}")

    key = LICENSE_KEYS.get(license_name)
    has_license = any((folder / f).exists() for f in ("LICENSE", "LICENSE.md", "LICENSE.txt"))
    if key and not has_license:
        res = _gh(path, "api", f"licenses/{key}", "--jq", ".body")
        if res.ok:
            owner = _git(path, "config", "user.name").output.strip()
            body = res.output
            for placeholder in ("[year]", "[yyyy]"):
                body = body.replace(placeholder, str(date.today().year))
            for placeholder in ("[fullname]", "[name of copyright owner]"):
                body = body.replace(placeholder, owner)
            (folder / "LICENSE").write_text(body + "\n", encoding="utf-8")
            log.append(f"Licencia {license_name} creada.")
        else:
            log.append(f"No se pudo descargar la licencia {license_name}: {res.output}")

    # --- primer commit ---
    if push:
        has_commits = _git(path, "rev-parse", "--verify", "HEAD").ok
        pending = _git(path, "status", "--porcelain").output.strip()
        if pending:
            note = ensure_identity(path)
            if note:
                log.append(note)
            for label, args in (
                ("git add -A", ("add", "-A")),
                ("git commit", ("commit", "-m", "Primer commit" if not has_commits else "Agrega archivos iniciales")),
            ):
                res = _git(path, *args)
                if not res.ok:
                    log.append(f"$ {label}\n{_explain_failure(res.output)}")
                    return Result(False, "\n".join(log))
            log.append("Primer commit hecho.")
        elif not has_commits:
            return Result(False, "La carpeta está vacía: no hay nada que subir. Agrega archivos o marca el README.")

    # --- crear en GitHub y enlazar ---
    args = ["repo", "create", name, "--private" if private else "--public", "--source=.", "--remote=origin"]
    if description:
        args += ["--description", description]
    if push:
        args.append("--push")
    res = _gh(path, *args, timeout=180)
    if not res.ok:
        log.append(_explain_failure(res.output))
        return Result(False, "\n".join(log))
    log.append(f"Repositorio creado{' y subido' if push else ''}: {res.output}")
    return Result(True, "\n".join(log))
