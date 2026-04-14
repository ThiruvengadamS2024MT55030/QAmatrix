import { QAMatrixEntry } from "@/types/qaMatrix";

const trimKeys = ["T10","T20","T30","T40","T50","T60","T70","T80","T90","T100","TPQG"] as const;
const chassisKeys = ["C10","C20","C30","C40","C45","P10","P20","P30","C50","C60","C70","RSub","TS","C80","CPQG"] as const;
const finalKeys = ["F10","F20","F30","F40","F50","F60","F70","F80","F90","F100","FPQG"] as const;
const qControlKeys = ["freqControl_1_1","visualControl_1_2","periodicAudit_1_3","humanControl_1_4","saeAlert_3_1","freqMeasure_3_2","manualTool_3_3","humanTracking_3_4","autoControl_5_1","impossibility_5_2","saeProhibition_5_3"] as const;

export function exportToCSV(data: QAMatrixEntry[], filename = "qa-matrix-export.csv") {
  const headers = [
    "S.No", "Source", "Operation Station", "Designation of the operation",
    "Concern Discerption [Mode of failure]", "Defect code", "Location code",
    "Defect Rating (1/3/5)", "Reccurence",
    "Last 6 Weeks", "Last 5 Weeks", "Last 4 Weeks", "Last 3 Weeks", "Last 2 Weeks", "Last Week",
    "Reccurence Count+Defect Rating",
    ...trimKeys,
    "C10","C20","C30","C40","C45","P10","P20","P30","C50","C60","C70","R/Sub","T/S","C80","C PQG",
    ...finalKeys, "Residual Torque",
    "1.1: Frequency Control", "1.2:Visual Control", "1.3:Periodic audit Process monitoring",
    "1.4:100% Human Control without tracking", "3.1:SAE(Error Proofing) alert",
    "3.2:Frequency control (Measurements)", "3.3:100% Manual control in the line with tool",
    "3.4:100% human control with tracking", "5.1:100% automatic control",
    "5.2:Impossibility of assembly or subsequent machining", "5.3:SAE(Error proofing) Prohibition",
    "CVT", "SHOWER", "Dynamic/ UB", "CC4",
    "MFG", "Quality", "Plant",
    "Wokstation", "MFG", "Plant",
    "MFG Action", "Resp", "Target"
  ];

  const rows = data.map(d => [
    d.sNo, d.source, d.operationStation, d.designation,
    `"${d.concern.replace(/"/g, '""')}"`,
    `"${(d.defectCode || "").replace(/"/g, '""')}"`,
    `"${(d.defectLocationCode || "").replace(/"/g, '""')}"`,
    d.defectRating, d.recurrence,
    ...d.weeklyRecurrence,
    d.recurrenceCountPlusDefect,
    ...trimKeys.map(k => d.trim[k] ?? ""),
    ...chassisKeys.map(k => d.chassis[k] ?? ""),
    ...finalKeys.map(k => d.final[k] ?? ""),
    d.final.ResidualTorque ?? "",
    ...qControlKeys.map(k => d.qControl[k] ?? ""),
    d.qControlDetail.CVT ?? "", d.qControlDetail.SHOWER ?? "", d.qControlDetail.DynamicUB ?? "", d.qControlDetail.CC4 ?? "",
    d.controlRating.MFG, d.controlRating.Quality, d.controlRating.Plant,
    d.workstationStatus, d.mfgStatus, d.plantStatus,
    `"${(d.mfgAction || "").replace(/"/g, '""')}"`,
    d.resp, d.target
  ]);

  const csv = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
