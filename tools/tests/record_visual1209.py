"""Record coordinator screenshot inspection; no screen-reader voice claim."""
import json
from init_onboarding1209 import ROOT,E,sha

def main():
    out=E/'VISUAL-01.json';assert not out.exists()
    paths=['gui04/onboarding-es-desktop.png','gui04/onboarding-de-mobile.png']
    record=dict(successful=True,method='Coordinator viewed both actual local PNGs with view_image after native Edge run',
        inspectedFiles={p:sha(E/p) for p in paths},findings=[],
        observations=['RC9 navigation and existing styles retained; canonical literal <img>/Unicode username and full UUID are readable.',
            'German390px screenshot wraps UUID and explanatory text within viewport; both continuation buttons remain visible.',
            'Password fields empty at capture; no synthetic passwords appear in the screenshots.'],
        limits=['Two inspected captures, not every screen/locale/theme.','No manual screen-reader voice or Wascar adoption.'])
    out.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(successful=True,capturesInspected=2)))

if __name__=='__main__':main()
