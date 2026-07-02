# 14 — Backup & Recovery

> Backup frequency, point-in-time recovery, disaster recovery, replication, recovery testing, recovery objectives.
> Implements ASD Section 17.5 and ASD Section 17.10.

---

## Recovery Objectives

| Objective | Target | Justification |
|---|---|---|
| **RPO (Recovery Point Objective)** | 15 minutes | The maximum data loss the business can tolerate. Achieved via WAL archiving (continuous). |
| **RTO (Recovery Time Objective)** | 4 hours | The maximum downtime for a full system recovery. Achieved via automated restore procedures and warm standby. |
| **RTO (partial — single-table restore)** | 1 hour | For accidental data deletion (e.g., a bad migration). Achieved via PITR to a specific timestamp. |

---

## Backup Strategy

### 1. Full Backups

- **Frequency**: daily (during low-traffic window, e.g., 2 AM UTC).
- **Method**: `pg_basebackup` (online, consistent snapshot of the entire database).
- **Compression**: enabled (reduces storage and transfer time).
- **Encryption**: encrypted with a separate backup key (not the production data encryption key).
- **Retention**: 30 days of daily backups.
- **Storage**: object storage (S3, GCS) in a different region than the primary (cross-region for disaster recovery).

### 2. Incremental Backups (WAL Archiving)

- **Frequency**: continuous (WAL segments archived as they are filled).
- **Method**: PostgreSQL WAL archiving (`archive_command` copies WAL segments to object storage).
- **Retention**: 30 days of WAL segments (matches the full backup retention).
- **Purpose**: enables point-in-time recovery (PITR) to any timestamp within the retention window.

### 3. Logical Backups (pg_dump)

- **Frequency**: weekly (in addition to physical backups).
- **Method**: `pg_dump` of selected schemas (for granular restore capability).
- **Retention**: 12 weeks of weekly logical backups.
- **Purpose**: enables schema-level or table-level restore without restoring the entire database.

### 4. Read Replica as a Live Backup

- **Purpose**: the read replica (per ASD Section 13.3) serves as a near-live backup; in a primary failure, the replica can be promoted.
- **Lag**: typically < 1 second; monitored with alerts if > 5 seconds.
- **Not a substitute for backups**: a replica does not protect against data corruption (a dropped table replicates to the replica).

---

## Point-in-Time Recovery (PITR)

PITR enables recovery to any timestamp within the WAL retention window (30 days).

**Procedure**:

1. **Restore the most recent full backup** taken before the target timestamp:
   ```bash
   pg_basebackup -D /var/lib/postgresql/recovery -X stream -C -S recovery_slot
   ```

2. **Configure recovery target**:
   ```
   restore_command = 'aws s3 cp s3://backup-bucket/wal/%f -'
   recovery_target_time = '2026-07-02 14:30:00+00'
   recovery_target_action = 'promote'
   ```

3. **Start PostgreSQL** in recovery mode:
   ```bash
   pg_ctl -D /var/lib/postgresql/recovery start
   ```

4. **PostgreSQL replays WAL segments** up to the recovery target, then promotes.

5. **Verify** the recovered data; reconfigure the application to point to the recovered instance.

**Use cases**:
- Accidental data deletion (e.g., a bad `DELETE` or `DROP`): recover to the timestamp just before the deletion.
- Data corruption (e.g., a bug that wrote invalid data): recover to the timestamp before the bug started.
- Forensic investigation: recover to a specific timestamp in a separate environment.

**Limitations**:
- PITR cannot recover individual rows; it recovers the entire database to a timestamp.
- The recovery window is limited by WAL retention (30 days). Beyond that, only full backups are available (recovery to the backup timestamp, not arbitrary timestamps).

---

## Disaster Recovery (DR)

### DR Architecture

- **Primary region**: the production deployment (e.g., `us-east-1`).
- **DR region**: a warm standby in a different region (e.g., `us-west-2`).
- **Cross-region replication**: PostgreSQL streaming replication from the primary to the DR region's standby (async, with < 5 second lag target).
- **Cross-region backups**: daily full backups and continuous WAL archiving to the DR region's object storage.

### DR Failover

In a primary-region failure:

1. **Detect failure**: automated health checks detect primary unavailability.
2. **Promote the DR standby**: the DR standby is promoted to primary.
3. **Reconfigure the application**: DNS or load balancer config is updated to point to the DR region.
4. **Verify**: the application is verified against the new primary.
5. **Communicate**: users are notified of the incident (per ASD Section 12.8 if PII is affected).

**RTO**: 4 hours (target; includes detection, promotion, reconfiguration, verification).

**RPO**: 15 minutes (the lag of the async replication; data written in the last 15 minutes before failure may be lost).

### DR Failback

Once the primary region is restored:

1. **Re-establish replication** from the DR region (now primary) to the restored primary region (now standby).
2. **Verify** replication lag is acceptable.
3. **Failback**: promote the original primary region; reconfigure the application.
4. **Verify** the application is serving from the original primary region.

**Failback is optional**: if the DR region is performing adequately, the team may choose to remain there until the next maintenance window.

### DR Drills

- **Frequency**: quarterly.
- **Method**: a full failover to the DR region in staging; periodically (annually) a full failover in production during a maintenance window.
- **Documentation**: each drill is documented (what was tested, what worked, what failed, action items).
- **Improvement**: drill findings drive runbook improvements and infrastructure changes.

---

## Replication

### Streaming Replication (Read Replica)

- **Purpose**: offload analytics reads; serve as a near-live backup.
- **Method**: PostgreSQL streaming replication (async).
- **Configuration**: the replica connects to the primary via TLS with client certificate authentication.
- **Lag monitoring**: `pg_stat_replication` on the primary; alerts if lag > 5 seconds.
- **Failover**: the replica can be promoted to primary in a primary failure (manual or automated via a tool like Patroni).

### Logical Replication (CDC)

- **Purpose**: feed the analytics warehouse (per ASD Section 13.7).
- **Method**: PostgreSQL logical replication (publications and subscriptions) or a CDC tool (Debezium).
- **Configuration**: a publication on the primary for the tables the warehouse consumes; a subscription on the warehouse side.
- **Schema evolution**: logical replication requires schema compatibility between publisher and subscriber; schema changes require coordinated migrations.

### Cross-Region Replication (DR)

- **Purpose**: disaster recovery.
- **Method**: streaming replication (async) from the primary region to the DR region's standby.
- **Configuration**: same as the read replica, but cross-region (higher latency; async to avoid write-latency impact).

---

## Recovery Testing

### Daily Backup Integrity Checks

- **Frequency**: daily.
- **Method**: restore the most recent daily backup into a sandbox environment; run a smoke test (connect, run a few queries); tear down.
- **Alert**: if the restore or smoke test fails, the on-call is paged.

### Weekly Full-Restore Drills

- **Frequency**: weekly.
- **Method**: restore the most recent weekly backup into a staging environment; run the full test suite against it; tear down.
- **Purpose**: verify that backups are restorable and that the restored database is functional.

### Quarterly DR Drills

- **Frequency**: quarterly.
- **Method**: full failover to the DR region (in staging); annually, full failover in production.
- **Purpose**: verify the DR architecture and the failover procedure.

### PITR Drills

- **Frequency**: monthly.
- **Method**: perform a PITR to a specific timestamp in a sandbox environment; verify the data matches expectations.
- **Purpose**: verify that WAL archiving is working and that PITR is functional.

---

## Backup Security

- **Encryption**: backups are encrypted with a separate key (not the production data encryption key).
- **Access control**: only the `dba` role can access backups; restore operations are audited.
- **Immutability**: backup objects in object storage are immutable (WORM — write once, read many) for the retention period, preventing accidental or malicious deletion.
- **Cross-region**: backups are stored in a different region than the primary, providing region-failure protection.

---

## Backup Retention Summary

| Backup Type | Frequency | Retention | Storage |
|---|---|---|---|
| Full (physical) | Daily | 30 days | Cross-region object storage (encrypted, immutable) |
| WAL (incremental) | Continuous | 30 days | Cross-region object storage (encrypted, immutable) |
| Logical (pg_dump) | Weekly | 12 weeks | Cross-region object storage (encrypted, immutable) |
| Read replica | Continuous | Live | Same region as primary (separate instance) |
| Cross-region replica | Continuous | Live | DR region (separate region) |

---

## Recovery Procedures (Runbooks)

### Runbook: Accidental Data Deletion (Bad Migration)

1. **Identify the timestamp** of the bad migration.
2. **Spin up a recovery instance** in a sandbox environment.
3. **Restore the most recent full backup** taken before the timestamp.
4. **Configure PITR** with `recovery_target_time` set to 1 minute before the bad migration.
5. **Start PostgreSQL in recovery mode**; wait for WAL replay to complete.
6. **Verify** the deleted data is present in the recovery instance.
7. **Export the deleted data** (via `pg_dump` of the affected tables).
8. **Import the deleted data** into the production database (via `pg_restore` or `INSERT`).
9. **Document** the incident in `audit_logs` and the incident response system.

**RTO**: 1 hour (target).

### Runbook: Primary Failure (Regional)

1. **Detect failure**: automated health checks confirm primary unavailability.
2. **Declare incident**: the on-call declares an incident and initiates DR failover.
3. **Promote the DR standby**: `pg_ctl promote` on the DR standby.
4. **Reconfigure DNS / load balancer**: point the application to the DR region.
5. **Verify**: the application is verified against the new primary.
6. **Communicate**: users are notified (per ASD Section 12.8 if PII is affected).
7. **Post-incident**: plan failback or remain in DR region per business decision.

**RTO**: 4 hours (target).

### Runbook: Data Corruption (Bug)

1. **Identify the bug** and the timestamp it started.
2. **Stop the bug**: deploy a fix or rollback the offending deployment.
3. **Assess the corruption**: query the affected tables to determine the scope.
4. **Decide**: can the corruption be fixed forward (via a data migration), or is PITR required?
5. **If PITR**: follow the "Accidental Data Deletion" runbook to recover to before the bug, then re-apply legitimate writes.
6. **If forward-fix**: write a data migration to correct the corruption; test in staging; apply in production.
7. **Document** the incident.

---

*End of Backup & Recovery.*
