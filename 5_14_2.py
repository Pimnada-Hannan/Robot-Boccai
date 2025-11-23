import pymcprotocol
import struct


def main():
    print("Hello World!")
    pymc3e = pymcprotocol.Type3E()
    #pymc3e.setaccessopt(commtype="binary")
    pymc3e.connect("192.168.0.200", 2001)
    if pymc3e._is_connected:
        cpu_type, cpu_code = pymc3e.read_cputype()
        print(cpu_type, cpu_code)

    # pymc3e.randomwrite(
    #     word_devices=["D50", "D55"],
    #     word_values=[1000, 2000],
    #     dword_devices=["D1004"],
    #     dword_values=[655362],
    # )

if __name__ == "__main__":
        main()
        print("Hello World!2222")
