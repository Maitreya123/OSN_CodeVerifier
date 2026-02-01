// SPDX-FileCopyrightText: 2024 The OpenSn Authors <https://open-sn.github.io/opensn/>
// SPDX-License-Identifier: MIT

#pragma once

#include "modules/linear_boltzmann_solvers/discrete_ordinates_problem/sweep/sweep.h"
#include "modules/linear_boltzmann_solvers/discrete_ordinates_problem/sweep/boundary/sweep_boundary.h"
#include "modules/linear_boltzmann_solvers/discrete_ordinates_problem/sweep/communicators/async_comm.h"
#include "modules/linear_boltzmann_solvers/discrete_ordinates_problem/sweep/fluds/fluds.h"
#include "framework/mesh/mesh.h"
#include "framework/logging/log.h"
#include <memory>

namespace opensn
{

class SweepChunk;

/// Angles for a given groupset
class AngleSet
{
public:
  /**
   * Construct an AngleSet.
   * \param id Unique id of the angleset.
   * \param num_groups Number of energy groups in the groupset.
   * \param spds Associated SPDS.
   * \param fluds Associated FLUDS.
   * \param angle_indices Angle indices associated with the angleset.
   * \param boundaries Sweep boundaries.
   */
  AngleSet(size_t id,
           size_t num_groups,
           const SPDS& spds,
           std::shared_ptr<FLUDS>& fluds,
           const std::vector<size_t>& angle_indices,
           std::map<uint64_t, std::shared_ptr<SweepBoundary>>& boundaries)
    : id_(id),
      num_groups_(num_groups),
      spds_(spds),
      fluds_(fluds),
      angles_(angle_indices.begin(), angle_indices.end()),
      boundaries_(boundaries)
  {
  }

  size_t GetID() const { return id_; }

  const SPDS& GetSPDS() const { return spds_; }

  FLUDS& GetFLUDS() { return *fluds_; }

  const std::vector<std::uint32_t>& GetAngleIndices() const { return angles_; }

  std::map<uint64_t, std::shared_ptr<SweepBoundary>>& GetBoundaries() { return boundaries_; }

  size_t GetNumGroups() const { return num_groups_; }

  /// Get the number of angles in the angleset.
  size_t GetNumAngles() const { return angles_.size(); }

  /// Check if the angleset has the given angle index.
  bool HasAngleIndex(std::uint32_t angle_index) const;

  /**
   * Add anglesets that must complete their sweep before this angle set begins its sweep.
   * \param dependent_angle_sets Set of dependent anglesets (output).
   */
  virtual void UpdateSweepDependencies(std::set<AngleSet*>& dependent_angle_sets) {}

  virtual AsynchronousCommunicator* GetCommunicator()
  {
    OpenSnLogicalError("Method not implemented");
  }

  /**
   * Initialize delayed upstream data.
   * @note This method gets called when a sweep scheduler is constructed.
   */
  virtual void InitializeDelayedUpstreamData() = 0;

  /// Return the maximum buffer size from the sweepbuffer.
  virtual int GetMaxBufferMessages() const = 0;

  /// Set the maximum buffer size for the sweepbuffer.
  virtual void SetMaxBufferMessages(int new_max) = 0;

  /**
   * Advance the work stages of an angleset.
   * This function checks for upstream data, execute sweep if permitted, and send downstream data.
   * Implementations differ based on the sweep algorithm.
   * \param sweep_chunk Sweep chunk to use for sweeping.
   * \param permission Permission status to execute sweep.
   * \note The sweep is only executed when data are received from other MPI ranks and the permission
   * is ``AngleSetStatus::EXECUTE``.
   */
  virtual AngleSetStatus AngleSetAdvance(SweepChunk& sweep_chunk, AngleSetStatus permission) = 0;

  /// Block the current thread until all send buffers are flushed.
  virtual AngleSetStatus FlushSendBuffers() = 0;

  /// Reset the sweep buffer.
  virtual void ResetSweepBuffers() = 0;

  /// Instruct the sweep buffer to receive delayed data.
  virtual bool ReceiveDelayedData() = 0;

  /// Get pointer to a boundary flux data.
  virtual const double* PsiBoundary(uint64_t boundary_id,
                                    unsigned int angle_num,
                                    uint64_t cell_local_id,
                                    unsigned int face_num,
                                    unsigned int fi,
                                    unsigned int g,
                                    bool surface_source_active) = 0;

  /// Get pointer to outbound reflected flux data.
  virtual double* PsiReflected(uint64_t boundary_id,
                               unsigned int angle_num,
                               uint64_t cell_local_id,
                               unsigned int face_num,
                               unsigned int fi) = 0;

  virtual ~AngleSet();

protected:
  /**
   * Unique ID of the angleset.
   * Each angleset has a unique ID starting from 0.
   */
  const size_t id_;
  /// @brief Number of energy groups in the groupset.
  const size_t num_groups_;
  /// Associated SPDS.
  const SPDS& spds_;
  /// Associated FLUDS.
  std::shared_ptr<FLUDS> fluds_;
  /// Angle indices associated with the angleset.
  std::vector<std::uint32_t> angles_;
  /// Sweep boundaries.
  std::map<uint64_t, std::shared_ptr<SweepBoundary>>& boundaries_;
  /// Flag indicating if the angleset has completed its sweep.
  bool executed_ = false;
};

} // namespace opensn
