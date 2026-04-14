import * as XLSX from "xlsx";
import { QAMatrixEntry } from "@/types/qaMatrix";
import { recalculateStatuses } from "@/utils/qaCalculations";

function numOrNull(val: unknown): number | null {
  if (val === undefined || val === null || val === "" || val === " ") return null;
  const n = Number(val);
  return isNaN(n) ? null : n;
}

function str(val: unknown): string {
  if (val === undefined || val === null) return "";
  return String(val).trim();
}

export async function loadFromExcel(url: string): Promise<QAMatrixEntry[]> {
  const response = await fetch(url);
  const arrayBuffer = await response.arrayBuffer();
  const workbook = XLSX.read(arrayBuffer, { type: "array" });
  const sheet = workbook.Sheets[workbook.SheetNames[0]];
  const rows: unknown[][] = XLSX.utils.sheet_to_json(sheet, { header: 1 });

  let startIdx = 0;
  for (let i = 0; i < rows.length; i++) {
    const firstCell = rows[i]?.[0];
    if (typeof firstCell === "number" || (typeof firstCell === "string" && /^\d+$/.test(firstCell.trim()))) {
      startIdx = i;
      break;
    }
  }

  const entries: QAMatrixEntry[] = [];

  for (let i = startIdx; i < rows.length; i++) {
    const r = rows[i];
    if (!r || r.length < 10) continue;
    const sNo = Number(r[0]);
    if (isNaN(sNo) || sNo === 0) continue;

    // Columns: 0=S.No, 1=Source, 2=Station, 3=Designation, 4=Concern,
    // 5=Defect code, 6=Location code, 7=Defect Rating, 8=Recurrence,
    // 9-14=Weekly (W6..W1), 15=RC+DR, 16-26=Trim, 27-41=Chassis,
    // 42-52=Final+ResidualTorque, 53-63=QControl, 64-67=QCDetail,
    // 68-70=ControlRating, 71-73=Statuses, 74=MFGAction, 75=Resp, 76=Target

    const defectCode = str(r[5]);
    const defectLocationCode = str(r[6]);
    const defectRating = Number(r[7]) as 1 | 3 | 5;
    const weeklyRecurrence = [
      Number(r[9]) || 0, Number(r[10]) || 0, Number(r[11]) || 0,
      Number(r[12]) || 0, Number(r[13]) || 0, Number(r[14]) || 0,
    ];

    const trim = {
      T10: numOrNull(r[16]), T20: numOrNull(r[17]), T30: numOrNull(r[18]),
      T40: numOrNull(r[19]), T50: numOrNull(r[20]), T60: numOrNull(r[21]),
      T70: numOrNull(r[22]), T80: numOrNull(r[23]), T90: numOrNull(r[24]),
      T100: numOrNull(r[25]), TPQG: numOrNull(r[26]),
    };

    const chassis = {
      C10: numOrNull(r[27]), C20: numOrNull(r[28]), C30: numOrNull(r[29]),
      C40: numOrNull(r[30]), C45: numOrNull(r[31]), P10: numOrNull(r[32]),
      P20: numOrNull(r[33]), P30: numOrNull(r[34]), C50: numOrNull(r[35]),
      C60: numOrNull(r[36]), C70: numOrNull(r[37]), RSub: numOrNull(r[38]),
      TS: numOrNull(r[39]), C80: numOrNull(r[40]), CPQG: numOrNull(r[41]),
    };

    const final = {
      F10: numOrNull(r[42]), F20: numOrNull(r[43]), F30: numOrNull(r[44]),
      F40: numOrNull(r[45]), F50: numOrNull(r[46]), F60: numOrNull(r[47]),
      F70: numOrNull(r[48]), F80: numOrNull(r[49]), F90: numOrNull(r[50]),
      F100: numOrNull(r[51]), FPQG: numOrNull(r[52]), ResidualTorque: numOrNull(r[53]),
    };

    const qControl = {
      freqControl_1_1: numOrNull(r[54]), visualControl_1_2: numOrNull(r[55]),
      periodicAudit_1_3: numOrNull(r[56]), humanControl_1_4: numOrNull(r[57]),
      saeAlert_3_1: numOrNull(r[58]), freqMeasure_3_2: numOrNull(r[59]),
      manualTool_3_3: numOrNull(r[60]), humanTracking_3_4: numOrNull(r[61]),
      autoControl_5_1: numOrNull(r[62]), impossibility_5_2: numOrNull(r[63]),
      saeProhibition_5_3: numOrNull(r[64]),
    };

    const qControlDetail = {
      CVT: numOrNull(r[65]), SHOWER: numOrNull(r[66]),
      DynamicUB: numOrNull(r[67]), CC4: numOrNull(r[68]),
    };

    const wsStatusRaw = str(r[72]).toUpperCase();
    const mfgStatusRaw = str(r[73]).toUpperCase();
    const plantStatusRaw = str(r[74]).toUpperCase();

    const entry: QAMatrixEntry = {
      sNo,
      source: str(r[1]),
      operationStation: str(r[2]),
      designation: str(r[3]),
      concern: str(r[4]),
      defectCode,
      defectLocationCode,
      defectRating,
      recurrence: weeklyRecurrence.reduce((a, b) => a + b, 0),
      weeklyRecurrence,
      recurrenceCountPlusDefect: defectRating + weeklyRecurrence.reduce((a, b) => a + b, 0),
      trim, chassis, final, qControl, qControlDetail,
      controlRating: {
        MFG: numOrNull(r[69]),
        Quality: numOrNull(r[70]),
        Plant: numOrNull(r[71]),
      },
      guaranteedQuality: { Workstation: null, MFG: null, Plant: null },
      workstationStatus: (wsStatusRaw === "OK" ? "OK" : "NG"),
      mfgStatus: (mfgStatusRaw === "OK" ? "OK" : "NG"),
      plantStatus: (plantStatusRaw === "OK" ? "OK" : "NG"),
      mfgAction: str(r[75]),
      resp: str(r[76]),
      target: str(r[77]),
    };

    entries.push(recalculateStatuses(entry));
  }

  return entries;
}
