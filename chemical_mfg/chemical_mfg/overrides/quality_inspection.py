from erpnext.stock.doctype.quality_inspection.quality_inspection import QualityInspection

class CustomQualityInspection(QualityInspection):

    def set_readings_status(self):

        overall_status = "Accepted"

        for row in self.readings:

            # ---------- NUMERIC ----------
            if row.numeric:

                readings = [
                    row.reading_1, row.reading_2, row.reading_3, row.reading_4,
                    row.reading_5, row.reading_6, row.reading_7, row.reading_8,
                    row.reading_9, row.reading_10
                ]

                readings = [r for r in readings if r not in [None, ""]]

                # ✅ IGNORE EMPTY ROW
                if not readings:
                    row.status = ""
                    continue

                readings = [float(r) for r in readings]
                avg = sum(readings) / len(readings)

                if row.min_value <= avg <= row.max_value:
                    row.status = "Accepted"
                else:
                    row.status = "Rejected"
                    overall_status = "Rejected"

            # ---------- MANUAL ----------
            else:
                if not row.value:
                    row.status = ""
                    continue

                row.status = "Accepted"

        self.status = overall_status