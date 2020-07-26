def lensum(*args):
    return sum([len(arg) for arg in args])


def wrap_codeblock(content: str, *, split_paragraph: bool = False):
    blocks = []
    max_length = 2000
    prefix = '```md'
    postfix = '\n```'
    current = ''
    for line in content.split('\n'):
        if lensum(prefix, postfix, current, line) > max_length or (split_paragraph and not line.strip()):
            if current.strip():
                blocks.append(prefix + current + postfix)
            current = ''
        current += '\n' + line
    if current.strip():
        blocks.append(prefix + current + postfix)
    return blocks
