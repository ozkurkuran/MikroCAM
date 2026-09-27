# Streaming contract

## Pure preparation
core.cnc_job.PreparedJob(source:SourceSnapshot,report:PreflightReport,*,cancelled=None) is frozen.
Constructor recomputes analyze_gcode(source,report.setup), requires full equality and allowed=True.
Only source/report are caller inputs. Derived init=False fields: blocks(tuple[JobBlock]),
initial_machine_mm,final_machine_mm,g54_offset_mm,spindle_speeds(tuple[float]),ack_timeout_seconds.
No I/O; cooperative cancellation raises PreflightCancelled.
JobBlock(source_line:int,wire:bytes) frozen. Uppercase letters, exact numeric spelling, whitespace/
comments removed, LF terminated. gcode_lexer.Block.canonical holds that validated text.
validate_job_block(bytes) accepts one canonical supported012 block<=79bytes INCLUDING LF;
exclude M0/M1/comments/space/realtime/nonASCII/multiline/query/dollar syntax.
Require Placement matrix(1,0,0,1,xoff,yoff), supplied rapid rates and known positive duration.
Initial/final machine XYZ derive from existing placed_point/ModalInterpreter. G54=(xoff,yoff,zoff).
M3/M4 needs explicit positive S before/on block; track each active spindle speed including later
S changes. Live proof requires every used speed in $31..$30. M7/M8 mechanical confirmation only.
Watchdog=min(86400,max(30,10*nominal_seconds+30)); reject nominal duration>8640s. Exclude paused
wall time. Very slow overrides/acceleration may legitimately exceed this bound; fail without retry.

## Domain API
machine.job_models.JobPhase READY/PREPARING/RUNNING/PAUSING/PAUSED/COMPLETING/COMPLETE/ABORTED/FAILED
with lowercase values. JobObservation frozen fields: phase=READY,source_name='',source_sha256='',
acknowledged=0,total=0,source_line=None,diagnostic='',can_start=False,can_pause=False,
can_resume=False,can_stop=False,stop_unverified=False. Validate bounded strings/counts/flags.
StartJobRequest(job:PreparedJob,mechanical_confirmed:bool) frozen, exact type and True required.
MachineSnapshot.job defaults JobObservation(). Controller.request_job(request),pause_job(),
resume_job(),stop_job(); abort dispatches active job before manual. Add set_pause_check(callback)
beside existing set_interrupt_check. All methods owner-only; worker enqueues typed intents.

## Live admission and ACKs
No active manual/job, no taint/settings ACK, fresh verified Idle. $N requires unique empty N0/N1.
$$ requires unique finite $13/$30/$31/$32, matching report units,$32=0,0<=min<max and max>0;
all active spindle speeds within min/max. M5 M9 then $G requires G54/M5/M9. $# requires unique
full G54..59/G92/TLO, G92/TLO zero and G54 equals prepared offset within.005mm.
Then causal new Idle status with matching initial MPos/WCO before first source block.
No ordinary overlap. Queries3s/status freshness2s/poll250ms. Every ACK belongs to outstanding
purpose. Duplicate ACK in same received batch fails before next send. Unsolicited query evidence
during job fails. Process full batch before scheduling. Source watchdog permits planner/dwell waits.
Last ACK enters COMPLETING: M5 M9 using source watchdog (queued motion may delay); $G off readback;
new causal Idle at final MPos/WCO. No success from ACK alone.

## Pause and stop
Pause RUNNING/COMPLETING: stop feeding immediately, send !, await causal Hold:0/Idle<=3s.
Hold:1 remains PAUSING. Pending ACK retains owner. Pause does not promise output off.
Resume explicit same job/session only fresh Hold:0/Idle; ~ only from Hold:0. Restore prior phase,
require new running/idle proof before new block. Extend ordinary/final deadlines by held wall time.
Stop all phases: discard scheduled work; reset18 only current empty N proof, else84 warningparking.
Never85 for queued source motion. stop_unverified stays true, session locked until reconnect,
no retry/resume; preserve counts/terminal diagnostic through disconnect.
Priority flags after read and immediately before source write; pause defers feeding without fault.
Worker one pending typed intent. Close joins<=4s for bounded I/O or retains owner/window.

## Transport and UI
Transport.write retains manual allowlist. write_job(data:bytes)->int accepts validated canonical
block or exact !/~, implemented by real/Fake; partial write fails without retry. Fake distinguishes
queue acceptance/endpoint and holds/reset, plus scripted delayed/error injection.
Explicit preflight transfer; off-owner preparation; changed source/report clears pending preparation
and start. Active immutable job retains original identity/progress. New equipment checkbox per Start,
reset on input change/reconnect. Progress means accepted blocks, not percent physically machined.