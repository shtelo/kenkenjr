from __future__ import print_function

from apiclient import discovery
from httplib2 import Http
from oauth2client import client
from oauth2client import file
from oauth2client import tools

from utils import get_path

SCOPES = 'https://www.googleapis.com/auth/documents.readonly'
DISCOVERY_DOC = 'https://docs.googleapis.com/$discovery/rest?version=v1'

list_order = dict()


def get_prefix_of(list_id, nested):
    if nested is None:
        if list_id not in list_order:
            list_order[list_id] = 0
        list_order[list_id] += 1
        return str(list_order[list_id]) + '. '
    return '* '


def get_credentials():
    store = file.Storage(get_path('docs_token'))
    credentials = store.get()

    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(get_path('docs_credential'), SCOPES)
        credentials = tools.run_flow(flow, store)
    return credentials


def read_paragraph_element(element):
    """Returns the text in the given ParagraphElement.

        Args:
            element: a ParagraphElement from a Google Doc.
    """
    text_run = element.get('textRun')
    if not text_run:
        return ''
    return text_run.get('content')


def read_strucutural_elements(elements):
    text = ''
    for value in elements:
        if 'paragraph' in value:
            paragraph = value.get('paragraph')
            elements = paragraph.get('elements')
            if 'paragraphStyle' in paragraph:
                paragraph_style = paragraph.get('paragraphStyle')
                name = paragraph_style.get('namedStyleType')
                indent = paragraph_style.get('indentStart')
                if indent is not None and 'magnitude' in indent:
                    text += '  ' * (indent.get('magnitude') // 18)
                if name == 'TITLE':
                    text += '#'
                elif name == 'SUBTITLE':
                    text += '- '
                elif name == 'HEADING_1':
                    text += '\n# '
                elif name == 'HEADING_2':
                    text += '\n## '
                elif name == 'HEADING_3':
                    text += '### '
                elif name == 'HEADING_4':
                    text += '#### '
                elif name == 'HEADING_5':
                    text += '##### '
                elif name == 'HEADING_6':
                    text += '###### '
                if 'bullet' in paragraph:
                    bullet = paragraph.get('bullet')
                    if 'listId' in bullet:
                        text += get_prefix_of(bullet.get('listId'), bullet.get('nestingLevel'))
                    else:
                        text += '* '
            for elem in elements:
                text += read_paragraph_element(elem)
        elif 'table' in value:
            table = value.get('table')
            for row in table.get('tableRows'):
                cells = row.get('tableCells')
                for cell in cells:
                    text += read_strucutural_elements(cell.get('content'))
        elif 'tableOfContents' in value:
            toc = value.get('tableOfContents')
            text += '  ' + '\n  '.join(read_strucutural_elements(toc.get('content')).split('\n'))
    return text


def doc_read(doc_id):
    credentials = get_credentials()
    http = credentials.authorize(Http())
    docs_service = discovery.build('docs', 'v1', http=http, discoveryServiceUrl=DISCOVERY_DOC)
    doc = docs_service.documents().get(documentId=doc_id).execute()
    doc_content = doc.get('body').get('content')
    result = read_strucutural_elements(doc_content)
    # with open('./test.json', mode='w', encoding='utf-8') as f:
    #     json.dump(doc_content, f, indent=4, ensure_ascii=False)
    # with open('./stringified.txt', mode='w', encoding='utf-8') as f:
    #     f.write(result)
    list_order.clear()
    return result
