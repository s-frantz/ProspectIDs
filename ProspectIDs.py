class ProspectIDs:

    """
        Generates 'pids', a trie-esque dictionary of existing 9-character prospect_ids, decomposed into:
            - fips code: (primary dict key) [STR] the first 5 digits identifying the larger area, ie county, that the prospecting area of interest (AOI) belongs to
            - family: (nested dict key) [STR] the next 3 digits applying a numerical ID to the given prospecting area of interest (AOI) to differentiate between others in the county
            - letters: (nested dict value) [LIST OF STRs] the letter code applying alphabetical versioning to this specific prospecting area of interest (AOI), versus others in its family
        Example dict item:
            - fips_: {family1:[A, B], family2:[A]}
        Example methods using example item:
            - add("{}{}{}".format(fips_, family2, "B")), modifies dict item to:
                - fips_: {family1:[A, B], family2:[A, B]}
            - remove("{}{}{}".format(fips_, family2, "A")), modifies dict item to:
                - fips_: {family1:[A, B]}
            - next_available_family(fips_), returns:
                - "family3"
            - next_available_letter("{}{}".format(fips_, family1)), returns:
                - "C"
    """

    def __init__(self):
        self.pids = {}
        self._populate_pids_from_sql()

    def _populate_pids_from_sql(self):
        import sys
        sys.path.append(r"\\ace-ra-fs1\data\GIS\_Dev\python\apyx")
        import apyx
        q_apexaoi_to_find_prospectids = "{} and {} and {}".format(
            "LEN(Prospect_ID) = 9",
	        "TRY_CAST(LEFT(prospect_id, 8) AS INT) > 0",
            "RIGHT(Prospect_ID, 1) LIKE '%[a-zA-Z]%'",
        )
        q = "SELECT Prospect_ID FROM Apex_Project_Boundary WHERE {} ORDER BY Prospect_ID".format(q_apexaoi_to_find_prospectids)
        eng = apyx.CreateEngine("ace-ra-sql1", "Apex_ProjectData")
        result = eng.execute(q)
        prospect_ids = result.fetchall()
        for prospect_id in prospect_ids:
            fips, number, letter = self._decompose(prospect_id[0])
            self.pids.setdefault(fips, {}).setdefault(number, []).append(letter)

    def _decompose(self, pid):
        return pid[:5], pid[5:-1], pid[-1]

    def _is_valid(self, pid):
        if not type(pid) == str: return False
        if not len(pid) == 9: return False
        if not pid[:8].isnumeric(): return False
        if not pid[-1].isalpha(): return False
        return True

    def _is_novel(self, pid):
        fips, number, letter = self._decompose(pid)
        if fips in self.pids.keys():
            if number in self.pids[fips]:
                if letter in self.pids[fips][number]:
                    return False
        return True

    def is_numeric_string(self, S, length=False):
        """Returns True if input 'S' is (1) a string, (2) entirely numeric, and (3) - optionally - of specified length"""
        if not type(S) == str: return False
        if not S.isnumeric(): return False
        if length:
            if not len(S) == length: return False
        return True

    def add(self, pid):
        """Files the input prospect_id into the pids dictionary"""
        if not self._is_valid(pid):
            raise ValueError("ID: {} is invalid and could not be added - must be 8 digits + 1 letter".format(pid))
        if not self._is_novel(pid):
            raise ValueError("ID: {} already exists and therefore could not be added".format(pid))
        fips, number, letter = self._decompose(pid)
        self.pids.setdefault(fips, {}).setdefault(number, []).append(letter)

    def remove(self, pid):
        """Removes the input prospect_id from the pids dictionary"""
        if not self._is_valid(pid):
            raise ValueError("ID: {} is invalid and could not be added - must be 8 digits + 1 letter".format(pid))
        if self._is_novel(pid):
            raise ValueError("ID: {} does not already exist and therefore could not be removed".format(pid))
        fips, number, letter = self._decompose(pid)
        self.pids[fips][number] = [L for L in self.pids[fips][number] if L!=letter]
        if not self.pids[fips][number]:
            self.pids[fips] = [N for N in self.pids[fips] if N!=number]
            if not self.pids[fips]: del self.pids[fips]

    def next_available_family(self, fips):
        """Returns the next available numerical code or prospect_id family for the given fips code"""
        if not (self.is_numeric_string(fips, length=5)): raise ValueError("FIPS: {} is invalid - could not find next available number.".format(fips))
        numbers = [int(number) for number in self.pids[fips].keys()] if fips in self.pids.keys() else [0]
        next_with_free_above = max(numbers) + 1
        missing_ids = [x for x in range(1, max(numbers)+1) if x not in numbers] + [next_with_free_above]
        return str(missing_ids[0]).zfill(3)

    def next_available_letter(self, pid):
        """Returns the next available alphabetical version for the given prospect_id or prospect_id family"""
        if not (self._is_valid(pid) or self.is_numeric_string(pid, length=8)):
            raise ValueError("ID: {} is invalid and could not be added - must be 8 digits + 1 letter".format(pid))
        if len(pid) == 8: pid = "{}A".format(pid)
        fips, number, letter = self._decompose(pid)
        if fips in self.pids.keys():
            if number in self.pids[fips].keys():
                last_letter = self.pids[fips][number][-1]
                if last_letter == "Z": raise ValueError("Suffixes are maxed out (encountered 'Z') for id: {}".format(pid))
                return chr(ord(str(last_letter))+1) #returns next letter of the alphabet!
        return "A"