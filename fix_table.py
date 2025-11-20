import types


def fix():
    output = []
    buff: str = ""
    buffering: bool = False
    with open("table.md", "r") as f:
        while True:
            line = f.readline()
            if not line:
                break

            line = line.strip()
            print(line)

            if line.find("---|---") >= 0:
                output.append(buff)
                output.append(line)

                buff = ""
                continue

            if line.find("|") >= 0:
                if buff:
                    # print(replace_linebreaks(buff))
                    output.append(buff)
                buff = line
            else:
                if buff:
                    buff += "<br>" + line
                else:
                    output.append(line)

    with open("fix_table_result.md", "w") as f:
        for o in output:
            f.write(o + "\n")


fix()