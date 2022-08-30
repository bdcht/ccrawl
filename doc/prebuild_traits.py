from collections import defaultdict
from traitlets.config import Configurable
from traitlets.config.sphinxdoc import class_config_rst_doc
from ccrawl import conf

D = defaultdict(lambda: None)

with open("configuration.rst","w") as f:
    title = "Configuration"
    f.write(title+'\n'+'='*len(title)+'\n\n')

    for o in conf.__dict__.values():
        try:
            if 'Configurable' == o.mro()[1].__name__:
                f.write(class_config_rst_doc(o,D))
                f.write('\n')
        except Exception:
            pass
