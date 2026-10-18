// Verse of the day: one list for every reader, so a shared link to the home
// page shows the same verse to everyone on the same date.
const VERSES = [
	'PSA.119.105', 'JHN.3.16', 'PSA.23.1', 'PRO.3.5', 'ISA.40.31', 'JER.29.11', 'MAT.11.28', 'ROM.8.28',
	'PHP.4.13', 'PSA.46.1', 'ISA.41.10', 'MAT.6.33', 'JOS.1.9', 'ROM.12.2', '2CO.5.17', 'GAL.2.20',
	'EPH.2.8', 'PHP.4.6', 'HEB.11.1', 'JAS.1.5', '1PE.5.7', '1JN.1.9', 'REV.21.4', 'LAM.3.22',
	'MIC.6.8', 'PSA.27.1', 'PSA.37.4', 'PSA.91.1', 'ISA.53.5', 'JHN.14.6', 'JHN.11.25', 'ROM.5.8',
	'ROM.10.9', 'MAT.5.14', 'PSA.34.8', 'PSA.139.14', 'PRO.18.10', 'ISA.26.3', 'JHN.15.5', 'ROM.15.13',
	'2TI.1.7', 'HEB.13.8', 'PSA.103.2', 'ZEP.3.17', 'NUM.6.24', 'MAT.28.20', 'JHN.8.12', 'COL.3.23'
];

/** Today's verse id (`PSA.119.105`), by the reader's local date. */
export function verseOfDay(d = new Date()): string {
	const day = Math.floor(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / 864e5);
	return VERSES[day % VERSES.length];
}
