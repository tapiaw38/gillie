import { describe, expect, it } from 'vitest';
import * as THREE from 'three';
import type { VRM } from '@pixiv/three-vrm';
import { applyProceduralMotion } from './procedural-motion';
import type { AnimationType } from './animation-catalog';

const BONES = [
  'hips',
  'chest',
  'leftUpperArm',
  'rightUpperArm',
  'leftLowerArm',
  'rightLowerArm',
] as const;

type Bone = (typeof BONES)[number];

function rig() {
  const nodes = new Map<string, THREE.Object3D>();
  for (const name of BONES) nodes.set(name, new THREE.Object3D());
  const vrm = {
    humanoid: { getNormalizedBoneNode: (name: string) => nodes.get(name) ?? null },
  } as unknown as VRM;
  const baseRotations = new Map<Bone, THREE.Quaternion>(
    BONES.map((name) => [name, nodes.get(name)!.quaternion.clone()]),
  );
  return { nodes, vrm, baseRotations };
}

function move(
  target: ReturnType<typeof rig>,
  options: {
    animation?: AnimationType;
    audioLevel?: number;
    clipDriving?: boolean;
    speaking?: boolean;
    time?: number;
  } = {},
) {
  applyProceduralMotion(target.vrm, {
    animation: options.animation ?? 'IDLE',
    audioLevel: options.audioLevel ?? 0,
    baseRotations: target.baseRotations,
    clipDriving: options.clipDriving ?? false,
    speaking: options.speaking ?? false,
    time: options.time ?? 0.5,
  });
}

const IDENTITY = new THREE.Quaternion();

describe('applyProceduralMotion', () => {
  it('moves the body when no clip is driving it', () => {
    const target = rig();
    move(target);
    expect(target.nodes.get('chest')!.quaternion.angleTo(IDENTITY)).toBeGreaterThan(0);
  });

  it('lowers the arms out of the T-pose only when no clip poses them', () => {
    const solo = rig();
    const layered = rig();
    move(solo);
    move(layered, { clipDriving: true });

    expect(solo.nodes.get('leftUpperArm')!.quaternion.angleTo(IDENTITY)).toBeGreaterThan(0.4);
    expect(layered.nodes.get('leftUpperArm')!.quaternion.angleTo(IDENTITY)).toBeLessThan(0.1);
  });

  it('layers onto the pose a clip produced instead of discarding it', () => {
    const target = rig();
    const clipPose = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.9, 0, 0));
    target.nodes.get('leftUpperArm')!.quaternion.copy(clipPose);

    move(target, { animation: 'TALK', audioLevel: 0.5, clipDriving: true, speaking: true });

    const result = target.nodes.get('leftUpperArm')!.quaternion;
    expect(result.angleTo(clipPose)).toBeGreaterThan(0);
    expect(result.angleTo(clipPose)).toBeLessThan(0.3);
  });

  it('stays subtler while a clip is driving', () => {
    const layered = rig();
    const solo = rig();
    const options = { animation: 'TALK' as AnimationType, audioLevel: 1, speaking: true };
    move(layered, { ...options, clipDriving: true });
    move(solo, { ...options, clipDriving: false });

    expect(layered.nodes.get('chest')!.quaternion.angleTo(IDENTITY)).toBeLessThan(
      solo.nodes.get('chest')!.quaternion.angleTo(IDENTITY),
    );
  });

  it('does not drift when a clip keeps resetting the bones', () => {
    const target = rig();
    const clipPose = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.4, 0, 0));
    let worst = 0;

    for (let frame = 0; frame < 400; frame += 1) {
      target.nodes.get('chest')!.quaternion.copy(clipPose);
      move(target, {
        animation: 'TALK',
        audioLevel: 0.4,
        clipDriving: true,
        speaking: true,
        time: frame * 0.016,
      });
      worst = Math.max(worst, target.nodes.get('chest')!.quaternion.angleTo(clipPose));
    }

    expect(worst).toBeLessThan(0.2);
  });

  it('leaves the dance bounce to the clip when one is playing', () => {
    const layered = rig();
    const solo = rig();
    move(layered, { animation: 'DANCE', clipDriving: true, time: 1 });
    move(solo, { animation: 'DANCE', clipDriving: false, time: 1 });

    expect(layered.nodes.get('hips')!.quaternion.angleTo(IDENTITY)).toBeLessThan(
      solo.nodes.get('hips')!.quaternion.angleTo(IDENTITY),
    );
  });

  it('reacts to how loud the reply is while speaking', () => {
    const quiet = rig();
    const loud = rig();
    move(quiet, { animation: 'TALK', audioLevel: 0.05, speaking: true });
    move(loud, { animation: 'TALK', audioLevel: 1, speaking: true });

    expect(loud.nodes.get('leftLowerArm')!.quaternion.angleTo(IDENTITY)).toBeGreaterThan(
      quiet.nodes.get('leftLowerArm')!.quaternion.angleTo(IDENTITY),
    );
  });

  it('does not turn the body while a clip is driving it', () => {
    const target = rig();
    for (let frame = 0; frame < 200; frame += 1) {
      target.nodes.get('hips')!.quaternion.identity();
      move(target, { clipDriving: true, time: frame * 0.05 });
      const euler = new THREE.Euler().setFromQuaternion(
        target.nodes.get('hips')!.quaternion,
      );
      expect(Math.abs(euler.y)).toBeLessThan(1e-6);
      expect(Math.abs(euler.z)).toBeLessThan(1e-6);
    }
  });

  it('still sways when it is the only thing animating the body', () => {
    const target = rig();
    let widest = 0;
    for (let frame = 0; frame < 200; frame += 1) {
      move(target, { clipDriving: false, time: frame * 0.05 });
      const euler = new THREE.Euler().setFromQuaternion(
        target.nodes.get('hips')!.quaternion,
      );
      widest = Math.max(widest, Math.abs(euler.y));
    }
    expect(widest).toBeGreaterThan(0.02);
  });

  it('keeps the chest breathing even while a clip is driving', () => {
    const target = rig();
    let widest = 0;
    for (let frame = 0; frame < 200; frame += 1) {
      target.nodes.get('chest')!.quaternion.identity();
      move(target, { clipDriving: true, time: frame * 0.05 });
      const euler = new THREE.Euler().setFromQuaternion(
        target.nodes.get('chest')!.quaternion,
      );
      widest = Math.max(widest, Math.abs(euler.x));
    }
    expect(widest).toBeGreaterThan(0.005);
  });

  it('ignores a model without a humanoid rig', () => {
    expect(() =>
      applyProceduralMotion(null, {
        animation: 'IDLE',
        audioLevel: 0,
        baseRotations: new Map(),
        clipDriving: false,
        speaking: false,
        time: 0,
      }),
    ).not.toThrow();
  });
});
