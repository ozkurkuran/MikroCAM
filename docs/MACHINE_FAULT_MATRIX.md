# Makine hata senaryoları matrisi (C1)

Denetim tabanı: MikroCAM main `8680a09d`; 02.10.2026. Makine paketi 010/011/013/015/025'in
mevcut testleri önce incelendi. Legacy Levelling ayrı B1 kartıdır. Bu tablo yazılım/Fake kanıtıdır;
fiziksel durum için H protokolü gerekir. Bir hücredeki parantez, parametrik testin ilgili
varyantını belirtir. Aşağıdaki test adları `tests/` içindedir; dosya eşlemesi tablonun altındadır.

## Denetimdeki boşluklar ve sonuç

- ACK'in deadline'ın hemen altı/üstü: tüm sahiplerde alt sınır kanıtı eksikti; manual jog/zero
  ve iş ACK'i, durum raporu taze kalınca deadline sonrasında tüketilebiliyordu. Üç kırmızı
  regresyon (15 mevcut/yeni test geçti) sonrası iki küçük consume sınırı düzeltildi. Probe ve
  console zaten geç ACK'i reddediyordu. Hold süresinin deadline uzatması mevcut testle korundu.
- Bağlanma/manual/zero/probe/console/hold ACK parçalanması; job parçalanması zaten testliydi.
- Zero ve hold sırasında error/alarm/reset/stale/read/write; probe error/stale/write ve hareket
  başlatılmış jog error; diğer aktif yol örnekleri mevcut dosyalarda bulundu.
- OSError tabanlı USB testleri mevcut; SerialException'ın yedi sahipte read/write yolları eksikti.
- Door/Check/Sleep için zero/job/probe başlangıç reddi, işlem ortası geçişler, Check/Sleep hold
  resume reddi ve console non-Idle reddi eksikti. Var olan Idle zorunluluğu korunur.
- Eski sahibi düşüren on arka arkaya reconnect döngüsü altı aktif sahipte eksikti.

Yeni davranış (otomatik yeniden bağlanma/replay/restart) eklenmedi. Deadline düzeltmesi var olan
zaman aşımı sözleşmesinin hotfix'idir. 83 yeni parametrik test yalnızca bu boşlukları kapsar.

## Matris

| Senaryo | Bağlanma | Jog | İş sıfırı | İş akışı | Hold | Probe | Konsol |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ACK deadline hemen altı/üstü, status taze | test_ack_deadline_edges_keep_status_fresh(connect,before/after) | test_ack_deadline_edges_keep_status_fresh(jog,before/after) | test_ack_deadline_edges_keep_status_fresh(zero,before/after) | test_ack_deadline_edges_keep_status_fresh(job,before/after) | test_real_dwell_pending_ack_survives_long_verified_hold_without_resend | test_ack_deadline_edges_keep_status_fresh(probe,before/after) | test_ack_deadline_edges_keep_status_fresh(console,before/after) |
| `ok` parçalı read | test_fragmented_ack_preserves_owner_until_complete_line(connect) | test_fragmented_ack_preserves_owner_until_complete_line(jog) | test_fragmented_ack_preserves_owner_until_complete_line(zero) | test_fragmented_source_ack_never_releases_next_block_until_full_line | test_fragmented_ack_preserves_owner_until_complete_line(hold) | test_fragmented_ack_preserves_owner_until_complete_line(probe) | test_fragmented_ack_preserves_owner_until_complete_line(console) |
| `error:N` aktif işlemde | test_errors_do_not_leave_safe_state_or_unknown_units_as_zero(error:8) | test_missing_active_faults_stop_without_replaying_motion(jog,error) | test_missing_active_faults_stop_without_replaying_motion(zero,error) | test_controller_faults_discard_queue_and_never_retry(error:2); test_source_or_final_off_fault_never_reports_completion(error_reply) | test_missing_active_faults_stop_without_replaying_motion(hold,error) | test_missing_active_faults_stop_without_replaying_motion(probe,error) | test_fault_quarantines_without_invented_stop_and_late_ack_cannot_unlock(error:3) |
| `ALARM:N` aktif işlemde | test_errors_do_not_leave_safe_state_or_unknown_units_as_zero(ALARM:1) | test_failure_during_owned_move_locks_and_invalidates(alarm) | test_missing_active_faults_stop_without_replaying_motion(zero,alarm) | test_controller_faults_discard_queue_and_never_retry(ALARM:1) | test_missing_active_faults_stop_without_replaying_motion(hold,alarm) | test_probe_fault_never_commits_sample_or_sends_next_motion(alarm) | test_fault_quarantines_without_invented_stop_and_late_ack_cannot_unlock(ALARM:2) |
| `STATUS_TIMEOUT` | test_stale_invalidates_offset_and_unknown_state_is_not_idle; test_one_outstanding_status_timeout_retries_without_reopen | test_failure_during_owned_move_locks_and_invalidates(stale) | test_missing_active_faults_stop_without_replaying_motion(zero,stale) | test_ack_after_coordinates_become_stale_does_not_release_next_source | test_missing_active_faults_stop_without_replaying_motion(hold,stale) | test_missing_active_faults_stop_without_replaying_motion(probe,stale) | test_deadline_and_stale_query_fail_without_retry |
| USB read/write OSError / SerialException | test_io_failure_invalidates_and_closes(read/write); test_serial_exception_is_fail_closed_for_each_owner(connect,read/write) | test_failure_during_owned_move_locks_and_invalidates(read/write); test_serial_exception_is_fail_closed_for_each_owner(jog,read/write) | test_missing_active_faults_stop_without_replaying_motion(zero,read/write); test_serial_exception_is_fail_closed_for_each_owner(zero,read/write) | test_source_or_final_off_fault_never_reports_completion(read); test_job_transport_outcomes_log_requested_bytes_without_retry(exception); test_serial_exception_is_fail_closed_for_each_owner(job,read/write) | test_missing_active_faults_stop_without_replaying_motion(hold,read/write); test_serial_exception_is_fail_closed_for_each_owner(hold,read/write) | test_loss_of_live_evidence_stops_without_new_contact(disconnect); test_missing_active_faults_stop_without_replaying_motion(probe,write); test_serial_exception_is_fail_closed_for_each_owner(probe,read/write) | test_read_and_failed_close_errors_both_survive_final_snapshot; test_raw_fragments_and_final_failure_evidence_survive_disconnect; test_serial_exception_is_fail_closed_for_each_owner(console,read/write) |
| Beklenmeyen `Grbl 1.1` karşılama | test_reset_reacquires_units_without_overlapping_old_settings | test_failure_during_owned_move_locks_and_invalidates(reset) | test_missing_active_faults_stop_without_replaying_motion(zero,reset) | test_controller_faults_discard_queue_and_never_retry(Grbl) | test_missing_active_faults_stop_without_replaying_motion(hold,reset) | test_loss_of_live_evidence_stops_without_new_contact(reset) | test_fault_quarantines_without_invented_stop_and_late_ack_cannot_unlock(Grbl) |
| Beklenmeyen `GrblHAL` karşılama (042/043) | test_reset_to_different_firmware_reidentifies_before_motion; test_stop_resets_and_consistent_grblhal_banner_rereads_only_settings | test_grblhal_reset_banner_interrupts_every_owner_without_replay(jog) | test_grblhal_reset_banner_interrupts_every_owner_without_replay(zero) | test_grblhal_reset_banner_interrupts_an_owned_job; test_grblhal_reset_banner_interrupts_every_owner_without_replay(job) | Uygulanmaz: hold sırasında aynı iş reset yolu; grblHAL yeniden koşusu test_missing_active_faults_stop_without_replaying_motion(hold,reset) | test_grblhal_reset_banner_interrupts_every_owner_without_replay(probe) | test_grblhal_reset_banner_interrupts_every_owner_without_replay(console) |
| Firmware tanıma `error:`/zaman aşımı/sıra bozulması/bilinmeyen (042) | test_identification_error_is_unknown_but_settings_still_complete; test_identification_timeout_fails_closed_without_retry; test_settings_row_before_identification_ok_fails_closed; test_fragmented_identification_reply_keeps_ack_ownership | test_unsupported_profiles_disable_every_motion_owner_without_writes | test_unsupported_profiles_disable_every_motion_owner_without_writes | test_unsupported_profiles_disable_every_motion_owner_without_writes; test_character_counting_requires_session_budget | Uygulanmaz: iş kabul edilmez | test_unsupported_profiles_disable_every_motion_owner_without_writes | test_unsupported_profiles_disable_every_motion_owner_without_writes; test_settings_row_before_identification_ok_fails_closed |
| FluidNC v4.1.1 profili (044): bütün matris paketleri yeniden | test_fluidnc_fault_matrix.py (C1 + adversarial paketlerinin `__<modül>` kopyaları); test_port_open_reboot_waits_for_ready_board_before_identifying | test_jog_verifies_macros_and_auto_report_instead_of_n; test_boot_marker_during_jog_is_a_reset_without_extra_stop_bytes | test_zero_and_select_g54_complete_with_fluidnc_parameters; test_filled_macro_refuses_motion_and_never_authorizes_reset | test_send_response_job_completes_with_fluidnc_settings_proxies; test_custom_greeting_soft_reset_during_job_stops_and_reidentifies | test_hold_resume_and_stop_use_the_grbl_realtime_bytes | test_probe_grid_completes_and_tlo_vector_is_accepted; test_nonzero_tlo_vector_xy_refuses_probe_before_motion | test_console_config_dump_only_on_fluidnc_and_n_refused; test_console_settings_query_ignores_130_series_rows |
| Door / Check / Sleep | test_nonidle_state_cannot_start_manual_action(Door:0/Check/Sleep) | test_nonidle_state_cannot_start_manual_action; test_nonidle_transition_during_transaction_cannot_release_next_motion(jog) | test_nonidle_modes_reject_missing_operation_admission(zero); test_nonidle_transition_during_transaction_cannot_release_next_motion(zero) | test_nonidle_modes_reject_missing_operation_admission(job); test_nonidle_transition_during_transaction_cannot_release_next_motion(job) | test_resume_never_releases_wrong_machine_state(Door:0); test_hold_cannot_resume_from_check_or_sleep | test_nonidle_modes_reject_missing_operation_admission(probe); test_nonidle_transition_during_transaction_cannot_release_next_motion(probe) | test_console_nonidle_modes_reject_queries_without_movement; test_nonidle_transition_during_transaction_cannot_release_next_motion(console) |
| Feed hold sırasında kapatma | Uygulanmaz: salt okunur bağlantı feed hold sahibi değildir | Uygulanmaz: jog iptali 0x85'tir; test_disconnect_cancels_owned_jog_before_closing ayrı iptal yolunu kanıtlar | Uygulanmaz: sıfırlama atomik, feed hold işlemi yok | test_stop_or_disconnect_at_every_transaction_boundary_discards_job(pausing/paused,disconnect) | test_stop_or_disconnect_at_every_transaction_boundary_discards_job(paused,disconnect); test_failed_reset_or_door_delivery_retains_uncertainty_and_blocks_restart(paused) | Uygulanmaz: probe stop ayrı; test_priority_preserves_completed_samples(disconnect) | Uygulanmaz: hold sırasında konsol sahibi olamaz; test_console_cannot_reserve_or_write_through_any_active_job_boundary(paused) |
| Arka arkaya Connect/Disconnect | test_explicit_lifecycle_exact_allowlist_and_clean_reconnect; test_live_owner_queries_and_ten_reconnects_keep_final_log | test_repeated_reconnect_discards_prior_owner_without_replay(jog) | test_repeated_reconnect_discards_prior_owner_without_replay(zero) | test_repeated_reconnect_discards_prior_owner_without_replay(job); test_ten_real_qt_streaming_sessions_finish_and_release_both_owned_workers | test_repeated_reconnect_discards_prior_owner_without_replay(hold) | test_repeated_reconnect_discards_prior_owner_without_replay(probe) | test_repeated_reconnect_discards_prior_owner_without_replay(console); test_live_owner_queries_and_ten_reconnects_keep_final_log |

## Test dosyaları ve sınırlar

- [test_machine_fault_matrix.py](../tests/test_machine_fault_matrix.py): `test_ack_deadline_edges_keep_status_fresh`,
  `test_fragmented_ack_preserves_owner_until_complete_line`, `test_missing_active_faults_stop_without_replaying_motion`,
  `test_serial_exception_is_fail_closed_for_each_owner`, `test_nonidle_modes_reject_missing_operation_admission`,
  `test_hold_cannot_resume_from_check_or_sleep`, `test_console_nonidle_modes_reject_queries_without_movement`,
  `test_repeated_reconnect_discards_prior_owner_without_replay`,
  `test_nonidle_transition_during_transaction_cannot_release_next_motion`.
- [test_machine_controller.py](../tests/test_machine_controller.py): bağlantı, status, reset, settings ve I/O.
- [test_machine_manual_controller.py](../tests/test_machine_manual_controller.py): non-Idle admission.
- [test_machine_manual_stop.py](../tests/test_machine_manual_stop.py): aktif jog/USB/stale/reset/alarm/kapatma.
- [test_job_control.py](../tests/test_job_control.py): aktif iş fault ve hold/resume durumları.
- [test_job_adversarial.py](../tests/test_job_adversarial.py): fragment, stale, her transaction/hold kapatma,
  son kaynak/son off hataları, uzun hold ACK deadline uzatması.
- [test_console_control.py](../tests/test_console_control.py): fault karantinası, deadline/stale, USB write kanıtı.
- [test_console_adversarial.py](../tests/test_console_adversarial.py): USB read/close, job write failure ve hold exclusion.
- [test_console_panel.py](../tests/test_console_panel.py): on gerçek Qt reconnect ve retained log.
- [test_probe_failures.py](../tests/test_probe_failures.py): temas/probe fail, reset/USB, partial map ve disconnect.
- [test_firmware_controller.py](../tests/test_firmware_controller.py) (042): `$I` sahipliği, hata/zaman aşımı,
  farklı firmware resetinde yeniden tanıma, desteklenmeyen profillerde sıfır hareket baytı ve stop yolu.
- [test_job_ui.py](../tests/test_job_ui.py): on gerçek Qt job oturumu ve sahip worker kapanışı.
- [test_grblhal_controller.py](../tests/test_grblhal_controller.py) (043): grblHAL sahiplerinin uçtan uca
  akışları, her sahipte `GrblHAL` reset karşılaması, push `[GC:]`, desteklenmeyen kart/kip retleri.
- [test_grblhal_fault_suites.py](../tests/test_grblhal_fault_suites.py) (043): bu tablodaki bütün dosyaların
  (C1 matrisi, iş/manual/probe/konsol adversarial ve sahip paketleri) değiştirilmemiş testleri FakeGRBL
  `grblhal` varsayılanıyla yeniden koşulur; tek istisna gerekçesiyle dosyada (`EXCLUDED`).
- [test_fluidnc_fault_matrix.py](../tests/test_fluidnc_fault_matrix.py) (044): bu tablodaki
  `test_machine_fault_matrix`, `test_job_adversarial`, `test_machine_manual_stop`, `test_probe_failures`,
  `test_console_adversarial` ve `test_machine_controller` testlerinin FakeGRBL varsayılan profili
  `fluidnc` iken `<test>__<modül>` adıyla yeniden toplanması (235 test).
- [test_fluidnc_controller.py](../tests/test_fluidnc_controller.py) (044): FluidNC'ye özgü boot,
  özel karşılama, makro/`$RI`, `$$` vekil, TLO vektörü ve konsol senaryoları.

Matris her hücrede test adı veya sahiplik anlamına dayanan gerekçeli uygulanmaz içerir.
Denetim isimlerin kaynakta varlığını ve parametrik değerleri ayrıca kontrol eder; isim araması
tek başına davranış kanıtı değildir. Test gövdeleri gerçek MachineController/FakeGRBL/sahte saat
üzerindeki durum ve wire değişmezlerini assert eder. SerialException testleri yalnızca fake'e
exception enjekte eder. Full suite ve son commit Windows CI PR'a kaydedilir. Fiziksel doğrulama açık.
