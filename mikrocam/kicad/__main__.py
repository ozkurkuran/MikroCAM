"""Optional KiCad export helper, independent of the Qt application."""
import argparse
from pathlib import Path
from mikrocam.kicad.export import export_board


def main() -> int:
    parser=argparse.ArgumentParser(description='Export KiCad10 PCB production transfer for MikroCAM')
    parser.add_argument('board',type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--kicad-cli')
    args=parser.parse_args()
    try:
        print(export_board(args.board,args.output,kicad_cli=args.kicad_cli))
    except (ValueError,OSError) as error:
        parser.exit(2,str(error)+'\n')
    return 0


if __name__=='__main__':raise SystemExit(main())
