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
    """Analyze word syllables and stress patterns using CMU Pronouncing Dictionary.

    Args:
        word: The word to analyze.

    Returns:
        A list of dictionaries mapping syllables to their stress values (0-2),
        where 0 = unstressed, 1 = secondary stress, 2 = primary stress.
        Returns None if the word is not found in the dictionary.
    """
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
    """Render stress markers for a word in Emacs if it meets the minimum syllable count.

    Analyzes the word's syllable stress pattern and calls Emacs to render the
    stress markers visually. Only renders words that have at least
    `minimum_syllables` syllables.

    Args:
        word: The word to render stress markers for.
    """
    syllables_stress = analyze_word(word)
    stress_pos = []
    # print(syllables_stress)
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
    """Initialize syllable stress settings from Emacs variables.

    Fetches configuration values from Emacs, including the minimum syllable
    threshold for rendering stress markers. Prints a startup message when
    initialization is complete.
    """
    global minimum_syllables
    minimum_syllables = int(await get_emacs_var("syllable-stress-minimum-syllables"))
    print("Syllable Stress started.")


def handle_arg_types(arg):
    """Convert Lisp-style quoted string arguments into symbols when needed.

    Processes arguments for conversion to S-expressions. If the argument is a
    string starting with a single quote, it extracts the quoted content and
    converts it to a symbol. Otherwise, wraps the argument as a quoted
    S-expression.

    Args:
        arg: The argument to process.

    Returns:
        A sexpdata.Quoted wrapper around the processed argument.
    """
    if isinstance(arg, str) and arg.startswith("'"):
        arg = sexpdata.Symbol(arg.partition("'")[2])
    # print(arg)

    return sexpdata.Quoted(arg)


async def eval_in_emacs(method_name, args):
    """Evaluate an Emacs Lisp function call via the websocket bridge.

    Builds an S-expression from the method name and arguments, serializes it
    to Lisp syntax, and sends it to Emacs for evaluation.

    Args:
        method_name: The name of the Emacs Lisp function to call.
        args: List of arguments to pass to the function.
    """
    args = [sexpdata.Symbol(method_name)] + list(map(handle_arg_types, args))  # type: ignore
    sexp = sexpdata.dumps(args)
    print(sexp)
    await bridge.eval_in_emacs(sexp)


async def on_message(message):
    """Handle incoming WebSocket messages from Emacs.

    Parses JSON messages and dispatches commands. Currently supports:
    - "render-string": Extracts words from the string and renders stress markers
      for each unique word.

    Args:
        message: The raw WebSocket message string containing JSON.

    Note:
        Prints a message for unrecognized commands and logs any tracebacks
        when processing fails.
    """
    try:
        info = json.loads(message)
        print(info)
        cmd = info[1][0].strip()
        if cmd == "render-string":
            str = info[1][1].strip()
            words = re.findall(r"[A-Za-z]+", str)
            words = list(set(words))
            # print(words)
            for word in words:
                await render_word(word)

        else:
            print(f"not fount handler for {cmd}", flush=True)

    except Exception as _:
        import traceback

        print(traceback.format_exc())


async def main():
    """Main entry point for the syllable stress service.

    Registers the message handler with the WebSocket bridge, initializes
    transcription services, and runs initialization and bridge startup
    concurrently.
    """
    global bridge
    bridge = websocket_bridge_python.bridge_app_regist(on_message)
    await asyncio.gather(init(), bridge.start())


if __name__ == "__main__":
    asyncio.run(main())
