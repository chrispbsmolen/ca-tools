# smolen-2026-11-cas-published-data: arrays of other authors, published as data in the CAs package

HELD for the maintainer's decision: these are copies of other authors' published arrays, not new constructions.
Each has the cited best known size (42 arrays; four strength-6 arrays over 20,000 rows were left out because the submission check could not finish them in this environment), which had no array the table could give.

Construction: the original authors' own work, named per row in claims.csv and credited to them: arrays of
Wagner, Kampel and Simos (2021), covering perfect hash families of Wagner, Colbourn and Simos (2022) and of
Sherwood, Martirosyan and Colbourn (2006), arrays of Colbourn, Keri, Rivas Soriano and Schlage-Puchta (2010),
cover starters of Meagher and Stevens (2005), of Colbourn, Martirosyan, Mullen, Shasha, Sherwood and Yucas (2006)
and of Colbourn and Keri, and simulated annealing arrays of Cohen.
No Torres-Jimenez data (TJ2level_CAs, CAEX_CAs, TJcat, LCDST starters) is used; every array passed the fingerprint
screen against table/tj_fingerprints.csv and the withdrawn files.

Built from: the CAs 0.24.4 data and construction functions named in each row.

Program: programs/build.R (from this folder: Rscript programs/build.R claims.csv rebuilt) rebuilds every file.
Each array was checked exactly with ca_verify.
