"""Usage: !calc 2 + 2 * (5 - 1)"""

import ast
import operator

# Only these operators are allowed - no function calls, no attribute
# access, no arbitrary code execution. Safer than eval().
_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("Unsupported expression")


async def run(client, message, args):
    """Does basic math: + - * / ** % and parentheses"""
    expr = args.strip()
    if not expr:
        await message.channel.send("Usage: `!calc 2 + 2 * 3`")
        return

    try:
        tree = ast.parse(expr, mode="eval")
        result = _safe_eval(tree)
    except (ValueError, SyntaxError, ZeroDivisionError, TypeError):
        await message.channel.send("Couldn't calculate that - check your expression.")
        return

    await message.channel.send(f"{expr} = **{result}**")
