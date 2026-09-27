# Data model
PreparedJob owns exact SourceSnapshot/PreflightReport and derived immutable JobBlock tuple.
Initial/final machine XYZ and G54 use existing Placement. Active spindle speeds support live proof.
StartJobRequest carries prepared job and per-job mechanical confirmation. JobObservation carries
identity/count/source-line/phase/eligibility/diagnostic/stop uncertainty in MachineSnapshot.
JobControl owns one transaction, provisional records, continuation, query threshold, deadline and
source index. Terminal failure clears continuation and retains evidence. No persistence/queue.