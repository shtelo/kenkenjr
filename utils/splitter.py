def lensum(*args):
    return sum([len(arg) for arg in args])


def wrap_codeblock(content: str, *, max_length: int = 2000, split_paragraph: bool = False, markdown: str = 'md'):
    blocks = []
    prefix = '```' + markdown
    postfix = '\n```'
    current = ''
    if not content:
        return [prefix + '​' + postfix]
    for line in content.split('\n'):
        if lensum(prefix, postfix, current, line) > max_length or (split_paragraph and not line.strip()):
            if current.strip():
                blocks.append(prefix + current + postfix)
            current = ''
        current += '\n' + line
    if current.strip():
        blocks.append(prefix + current + postfix)
    return blocks


def split_by_length(content: str, *, max_length: int = 2000):
    return [content[i:i+max_length] for i in range(0, len(content), max_length)]
