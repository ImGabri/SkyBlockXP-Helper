#!/usr/bin/env python3
"""Build a deterministic, self-contained executor script from the Rojo sources."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import NamedTuple


class BuildError(ValueError):
    """The source tree cannot be safely resolved into one script."""


class Token(NamedTuple):
    kind: str
    value: str
    start: int
    end: int


_LONG_OPEN = re.compile(r"\[(=*)\[")
_INIT_NAMES = {"init.luau", "init.client.luau", "init.server.luau"}
_ENTRY = "init.client.luau"


def _tokens(source: str) -> list[Token]:
    """Lex enough Luau to distinguish real require calls from strings/comments."""
    result = []
    index = 0
    while index < len(source):
        char = source[index]
        if char.isspace():
            index += 1
            continue
        if source.startswith("--", index):
            long = _LONG_OPEN.match(source, index + 2)
            if long:
                closing = "]" + long.group(1) + "]"
                finish = source.find(closing, long.end())
                if finish < 0:
                    raise BuildError("Unterminated long comment")
                index = finish + len(closing)
            else:
                finish = source.find("\n", index)
                index = len(source) if finish < 0 else finish + 1
            continue
        if char in "\"'":
            start = index
            index += 1
            while index < len(source):
                if source[index] == "\\":
                    index += 2
                elif source[index] == char:
                    index += 1
                    break
                else:
                    index += 1
            else:
                raise BuildError("Unterminated quoted string")
            result.append(Token("string", source[start:index], start, index))
            continue
        long = _LONG_OPEN.match(source, index)
        if long:
            closing = "]" + long.group(1) + "]"
            finish = source.find(closing, long.end())
            if finish < 0:
                raise BuildError("Unterminated long string")
            finish += len(closing)
            result.append(Token("string", source[index:finish], index, finish))
            index = finish
            continue
        if char.isalpha() or char == "_":
            start = index
            index += 1
            while index < len(source) and (source[index].isalnum() or source[index] == "_"):
                index += 1
            result.append(Token("identifier", source[start:index], start, index))
            continue
        result.append(Token("punctuation", char, index, index + 1))
        index += 1
    return result


def _literal_name(token: Token) -> str:
    text = token.value
    if token.kind != "string" or text[:1] not in {"'", '"'}:
        raise BuildError("Module names must be quoted string literals")
    name = text[1:-1]
    if not name or "\\" in name or "\n" in name or "\r" in name:
        raise BuildError("Module names must be nonempty, unescaped string literals")
    return name


def discover_sources(source_root: Path) -> tuple[dict[str, str], dict[tuple[str, ...], str]]:
    """Map filesystem sources to the Instance paths used by Rojo's init convention."""
    if not source_root.is_dir():
        raise BuildError(f"Missing source directory: {source_root}")
    sources = {}
    instances = {}
    all_paths = list(source_root.rglob("*"))
    for path in all_paths:
        if path.is_symlink():
            raise BuildError(f"Source symlinks are unsupported: {path}")
    directories = {
        path.relative_to(source_root).parts
        for path in all_paths
        if path.is_dir()
    }
    for path in sorted(source_root.rglob("*.luau")):
        if path.is_symlink():
            raise BuildError(f"Source symlinks are unsupported: {path}")
        relative = path.relative_to(source_root)
        key = relative.as_posix()
        if path.name in _INIT_NAMES:
            instance = relative.parent.parts
        else:
            name = path.stem
            if name.endswith((".client", ".server")):
                name = name.rsplit(".", 1)[0]
            instance = relative.parent.parts + (name,)
            if instance in directories:
                raise BuildError(f"Rojo file/folder collision at {'/'.join(instance)}")
        if instance in instances:
            raise BuildError(f"Duplicate Rojo instance: {instances[instance]} and {key}")
        instances[instance] = key
        sources[key] = path.read_text(encoding="utf-8")
    if _ENTRY not in sources:
        raise BuildError(f"Missing client entry point: {_ENTRY}")
    return sources, instances


def _resolve_expression(
    expression: list[Token], current: tuple[str, ...], nodes: set[tuple[str, ...]],
) -> tuple[str, ...]:
    if not expression or expression[0].value != "script":
        raise BuildError("Only static require(script...) calls can be bundled")
    instance = current
    index = 1
    while index < len(expression):
        token = expression[index].value
        if token == "." and index + 1 < len(expression):
            name = expression[index + 1]
            if name.kind != "identifier":
                raise BuildError("Expected an Instance name after '.'")
            if name.value == "Parent":
                if not instance:
                    raise BuildError("Require escapes the client source root")
                instance = instance[:-1]
            else:
                instance += (name.value,)
            index += 2
        elif token == "[" and index + 2 < len(expression) and expression[index + 2].value == "]":
            instance += (_literal_name(expression[index + 1]),)
            index += 3
        elif (
            token == ":"
            and index + 4 < len(expression)
            and expression[index + 1].value in {"WaitForChild", "FindFirstChild"}
            and expression[index + 2].value == "("
            and expression[index + 4].value == ")"
        ):
            instance += (_literal_name(expression[index + 3]),)
            index += 5
        else:
            raise BuildError("Unsupported or dynamic Instance expression in require")
        if instance not in nodes:
            raise BuildError(f"Unknown source Instance: {'/'.join(instance)}")
    return instance


def rewrite_requires(
    source: str,
    source_name: str,
    instances: dict[tuple[str, ...], str],
) -> str:
    current = next(path for path, name in instances.items() if name == source_name)
    nodes = {()}
    for path in instances:
        nodes.update(path[:index] for index in range(1, len(path) + 1))
    tokens = _tokens(source)
    replacements = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.value != "require" or token.kind != "identifier":
            index += 1
            continue
        if index and tokens[index - 1].value in {".", ":"}:
            index += 1
            continue
        if index + 1 < len(tokens) and (
            tokens[index + 1].kind == "string" or tokens[index + 1].value == "{"
        ):
            raise BuildError(f"{source_name}: Only parenthesized static require(script...) calls can be bundled")
        if index + 1 >= len(tokens) or tokens[index + 1].value != "(":
            # Native require can be passed to pcall for protected game modules.
            index += 1
            continue
        finish = index + 2
        depth = 1
        while finish < len(tokens) and depth:
            if tokens[finish].value == "(":
                depth += 1
            elif tokens[finish].value == ")":
                depth -= 1
            if depth:
                finish += 1
        if depth:
            raise BuildError(f"{source_name}: Unterminated require call")
        try:
            target_path = _resolve_expression(tokens[index + 2:finish], current, nodes)
            if target_path not in instances:
                raise BuildError(f"Unknown source module: {'/'.join(target_path) or '<root>'}")
            target = instances[target_path]
        except BuildError as exc:
            raise BuildError(f"{source_name}: {exc}") from exc
        replacements.append((token.start, tokens[finish].end, f"__require({json.dumps(target, ensure_ascii=False)})"))
        index = finish + 1
    for start, finish, replacement in reversed(replacements):
        source = source[:start] + replacement + source[finish:]
    return source


def build_bundle(source_root: Path) -> str:
    sources, instances = discover_sources(source_root)
    pieces = [
        "-- Generated by scripts/build.py; edit src/client instead.\n",
        "-- Self-contained bundle: no remote loaders or downloaded dependencies.\n",
        "local __factories = {}\n",
    ]
    for name, source in sources.items():
        rewritten = rewrite_requires(source, name, instances)
        pieces.append(f"\ndo\n__factories[{json.dumps(name, ensure_ascii=False)}] = function(__require)\n")
        pieces.append(rewritten.rstrip() + "\nend\nend\n")
    pieces.append('''
local __cache = {}
local __loaded = {}
local __loading = {}
local function __require(name)
    if __loaded[name] then
        return __cache[name]
    end
    if __loading[name] then
        error("Circular module dependency: " .. name, 2)
    end
    local factory = __factories[name]
    if not factory then
        error("Unknown bundled module: " .. name, 2)
    end
    __loading[name] = true
    local ok, result = pcall(factory, __require)
    __loading[name] = nil
    if not ok then
        error("Module " .. name .. " failed: " .. tostring(result), 2)
    end
    __loaded[name] = true
    __cache[name] = result
    return result
end

return __require("init.client.luau")
''')
    return "".join(pieces)


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if the existing bundle is missing or stale")
    parser.add_argument("--source-dir", type=Path, default=root / "src/client")
    parser.add_argument("--output", type=Path, default=root / "dist/PetSimAutomation.lua")
    args = parser.parse_args(argv)
    try:
        result = build_bundle(args.source_dir)
        if args.check:
            if not args.output.is_file() or args.output.read_bytes() != result.encode("utf-8"):
                raise BuildError(f"Bundle is missing or stale: {args.output}; run python3 scripts/build.py")
            print(f"Bundle is current: {args.output}")
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(result.encode("utf-8"))
            print(f"Built {args.output}")
    except (BuildError, OSError, UnicodeError) as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
