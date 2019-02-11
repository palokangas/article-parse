import sys
from parsecontrol import extract

def main(source_pdf=None):
    """Main entry to the script"""
    if source_pdf is None:
        print("Please provide path to source pdf for parsing.")
        return
    else:
        print("Starting non-interactive parsing.")
        return extract(source_pdf)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        print("syntax: parse.py [path_to_pdf]")
        sys.exit(1)
    else:
        results = main(sys.argv[1])
        if len(results) > 0:
            for result in results:
                print(result)
