import clang.cindex
clang.cindex.Config.library_file = 'libclang-6.0.so'
from ccrawl.parser import *
index = Index.create()
tu = index.parse('header.h',['-ferror-limit=0','-fparse-all-comments', '-M', '-MG'],
                 [],
                 TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD|\
                 TranslationUnit.PARSE_INCOMPLETE|\
                 TranslationUnit.PARSE_SKIP_FUNCTION_BODIES)
errs = list(tu.diagnostics)
pool = [c for c in tu.cursor.get_children()]


