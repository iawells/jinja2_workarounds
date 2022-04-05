from jinja2 import Environment, TemplateSyntaxError
from jinja2.ext import Extension
import re


def _improved_include_statement(block_start, block_end):
    return re.compile(fr"""
        (?P<lead> ^ .*)  # first group: greedy tokens at the beginning of the line
        {re.escape(block_start)}
        (?P<block_start_modifier> [\+|-]?)
        \s* indented-include \b   # keyword
        (?P<statement_args> .*? )
        (?P<block_end_modifier> [\+|-]?)
        {re.escape(block_end)}
        """,
        flags=re.MULTILINE|re.VERBOSE)


class MultiLineInclude(Extension):

    def preprocess(self, source, name, filename=None):
        """Swap out includes that have our additional command.

        We look in the template for indented-include directives, and
        swap them out for a chunk of text that includes the whitespace
        at the start of the line preceding the directive.

        This will not allow non-whitespace before the include
        directive; it will also not allow multiple 'indented-include'
        directives on the same line. TODO test
        """
        env: Environment = self.environment

        block_start: str = env.block_start_string
        block_end: str = env.block_end_string
        pattern = _improved_include_statement(block_start=block_start, block_end=block_end)
        re_newline = re.compile('\n')

        def add_indentation_filter(match):
            lead = match.group('lead')
            statement_args = match.group('statement_args')

            # guard against invalid use of improved include statement
            # line before include statement must be empty or indentation only
            if lead != '' and not lead.isspace():
                start_position = match.start('lead')
                lineno = len(re_newline.findall(source, 0, start_position)) + 1
                raise TemplateSyntaxError(
                    "line contains non-whitespace characters before include statement",
                    lineno,
                    name,
                    filename,
                )

            block_start_modifier = match.group('block_start_modifier')
            block_end_modifier = match.group('block_end_modifier')

            # Note that 'lead' consists only of whitespace, so
            # there's no Bobby Tables here where it is trying to be a
            # Jinja2 command

            # Note that we have to indent the first line; subsequent
            # lines are indented using the filter, but the leadin is
            # not.
            start_filter = lead + f'{block_start + block_start_modifier} filter indent("{lead}") {block_end}'
            include_statement = f'{block_start} include {statement_args} {block_end}'
            end_filter = f'{block_start} endfilter {block_end_modifier + block_end}'

            print(start_filter + include_statement + end_filter)
            return start_filter + include_statement + end_filter

        return pattern.sub(add_indentation_filter, source)
