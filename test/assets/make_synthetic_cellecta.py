"""Builds synthetic_cellecta_R{1,2}.fastq.gz: Cellecta DriverMap AIR-shaped reads for the block test.

Source: MiXCR's own public UMI fixture (tools/mixcr src/test/resources/sequences/
umi_ig_data_2_subset_R{1,2}.fastq.gz, also in mixcr-clonotyping's test/assets). R2 loses its
SMART TSO and UMI, and gains one of the kit's staggered MIVBC validator barcodes, so the
`cellecta-human-rna-xcr-mivbc-drivermap-air-v2` tag pattern matches. Each molecule is written
three times with random barcodes, giving the VBC filter several barcodes per clone.

Usage: python3 make_synthetic_cellecta.py <dir with umi_ig_data_2_subset_R{1,2}.fastq.gz>
"""

import gzip
import random
import sys

BARCODES = ["GCATCAA", "AGTCGTA", "TCGCATCA", "AGCGTAGA", "TACGACTA", "CTGATGAA"]
TSO = "TGGTATCAACGCAGAGT"
UMI_LENGTH = 16
COPIES = 3


def main(src: str) -> None:
    random.seed(7)
    with gzip.open(f"{src}/umi_ig_data_2_subset_R1.fastq.gz", "rt") as f:
        r1 = f.read().splitlines()
    with gzip.open(f"{src}/umi_ig_data_2_subset_R2.fastq.gz", "rt") as f:
        r2 = f.read().splitlines()
    with (
        gzip.open("synthetic_cellecta_R1.fastq.gz", "wt") as o1,
        gzip.open("synthetic_cellecta_R2.fastq.gz", "wt") as o2,
    ):
        for i in range(0, len(r1), 4):
            seq2, qual2 = r2[i + 1], r2[i + 3]
            k = seq2.find(TSO)
            if k >= 0:
                cut = k + len(TSO) + UMI_LENGTH
                seq2, qual2 = seq2[cut:], qual2[cut:]
            for copy in range(COPIES):
                bc = random.choice(BARCODES)
                o1.write(f"@r{i}_{copy}\n{r1[i + 1]}\n+\n{r1[i + 3]}\n")
                o2.write(f"@r{i}_{copy}\n{bc}{seq2}\n+\n{'I' * len(bc)}{qual2}\n")


if __name__ == "__main__":
    main(sys.argv[1])
