#!/usr/bin/env python3
# /// script
# dependencies = [
#   "syllabreak @ git+https://github.com/apakabarlabs/syllabreak-python.git",
#   "cmudict",
#   "sexpdata",
#   "websocket_bridge_python",
#   "python-socks"
# ]
# ///
from syllabreak import Syllabreak

import re
import cmudict
import asyncio
import json
import sexpdata
import websocket_bridge_python

SYLLABREAK = Syllabreak(" ")
CMU = cmudict.dict()
_stress_re = re.compile(r"([A-Z]+)([0-2])?$")


def get_stress(phone: str):
    """Extract stress digit from ARPABET phone."""
    m = _stress_re.fullmatch(phone)
    if not m:
        return None
    return m.group(2)


def analyze_word(word: str):
    w = word.lower()
    prons = CMU.get(w, [])
    if not prons:
        return None

    syllables = SYLLABREAK.syllabify(w, lang="eng").split()
    results = []
    for pron in prons:
        stress = [int(x) for x in (get_stress(p) for p in pron) if x is not None]
        # stress = list(set(stress))
        syllables_stress = dict(zip(syllables, stress))
        results.append(syllables_stress)
    # print(results)
    return results


async def render_word(word: str):
    syllables_stress = analyze_word(word)
    stress_pos = []
    if syllables_stress:
        syllable = syllables_stress[0]
        # print(syllable)
        # print(len(syllable) >= minimum_syllables)
        if len(syllable) >= minimum_syllables:
            for key in syllable:
                stress_pos.append([len(key), syllable[key]])
            await eval_in_emacs("syllable-stress-render-word", [{word: stress_pos}])


async def get_emacs_var(var_name: str):
    """Fetch an Emacs variable value by name, normalize quoted string results, log the resolved value, and return None when the value is null."""
    var_value = await bridge.get_emacs_var(var_name)
    if isinstance(var_value, str):
        var_value = var_value.strip('"')
    print(f"{var_name} : {var_value}")
    if var_value == "null":
        return None
    return var_value


async def init():
    """Initialize transcription settings from Emacs variables, select and instantiate the configured transcription backend, display startup status information, and launch the asynchronous transcription loop."""
    global minimum_syllables
    minimum_syllables = int(await get_emacs_var("syllable-stress-minimum-syllables"))
    print("Syllable Stress started.")


def handle_arg_types(arg):
    """Convert Lisp-style quoted string arguments into symbols when needed and return the argument wrapped as a quoted S-expression."""
    if isinstance(arg, str) and arg.startswith("'"):
        arg = sexpdata.Symbol(arg.partition("'")[2])
    # print(arg)

    return sexpdata.Quoted(arg)


async def eval_in_emacs(method_name, args):
    """Build an Emacs Lisp S-expression from the method name and processed arguments, serialize it, and asynchronously evaluate it in Emacs through the bridge."""
    args = [sexpdata.Symbol(method_name)] + list(map(handle_arg_types, args))  # type: ignore
    sexp = sexpdata.dumps(args)
    print(sexp)
    await bridge.eval_in_emacs(sexp)


async def on_message(message):
    """Parse an incoming message payload, dispatch the toggle command to recording control when requested, report unknown commands, and print a traceback if processing fails."""
    try:
        info = json.loads(message)
        print(info)
        cmd = info[1][0].strip()
        if cmd == "render-string":
            str = info[1][1].strip()
            words = re.findall(r"[A-Za-z]+", str)
            words = list(set(words))
            for word in words:
                await render_word(word)

        else:
            print(f"not fount handler for {cmd}", flush=True)

    except Exception as _:
        import traceback

        print(traceback.format_exc())


async def main():
    """Register the message handler with the websocket bridge, initialize transcription services, and run initialization and bridge startup concurrently."""
    global bridge
    bridge = websocket_bridge_python.bridge_app_regist(on_message)
    await asyncio.gather(init(), bridge.start())


if __name__ == "__main__":
    asyncio.run(main())
