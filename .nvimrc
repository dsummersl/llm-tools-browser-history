" lua << EOF
" require('lazy-loader')()
" EOF


let g:projectionist_heuristics = {
      \ 'pyproject.toml': {
      \   '*.py': {
      \     'type': 'function',
      \     'alternate': [
      \       'tests/{dirname}test_{basename}.py',
      \       'tests/{dirname}/test_{basename}.py',
      \     ]
      \   },
      \   'tests/**/test_*.py': {
      \     'type': 'test',
      \     'alternate': [
      \       '{dirname}{basename}.py',
      \       '{dirname}/{basename}.py',
      \     ]
      \   },
      \ },
      \ }
