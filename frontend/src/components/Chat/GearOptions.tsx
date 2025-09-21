import React from 'react';
import { Settings, Globe, Cog, RotateCcw, X } from 'lucide-react';

interface GearOptionsProps {
  onSelectOption: (description: string) => void;
  onEndConversation: () => void;
  show: boolean;
}

const gearOptions = [
  {
    key: 'gear_pair',
    title: '기어 쌍 (Gear Pair)',
    description: '두 개의 기어가 맞물리는 기본 구조로 설계해 주세요',
    icon: Settings,
    color: 'from-blue-500 to-blue-600',
  },
  {
    key: 'three_gear',
    title: '3단 기어 (Three Gear)',
    description: '세 개의 기어가 연결된 구조로 설계해 주세요',
    icon: Cog,
    color: 'from-green-500 to-green-600',
  },
  {
    key: 'simple_planetary',
    title: '단순 유성기어 (Simple Planetary)',
    description: '단순 유성기어로 설계해 주세요',
    icon: Globe,
    color: 'from-purple-500 to-purple-600',
  },
  {
    key: 'double_pinion',
    title: '이중 피니언 유성기어 (Double Pinion)',
    description: '더블 피니언 유성기어 시스템으로 설계해 주세요',
    icon: RotateCcw,
    color: 'from-orange-500 to-orange-600',
  },
];

export const GearOptions: React.FC<GearOptionsProps> = ({
  onSelectOption,
  onEndConversation,
  show,
}) => {
  if (!show) return null;

  return (
    <div className="border-t bg-white p-6">
      <div className="max-w-4xl mx-auto">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            🔧 설계 가능한 기어 타입 선택
          </h3>
          <p className="text-sm text-gray-600">
            원하는 기어 타입을 선택하여 설계를 시작하세요.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          {gearOptions.map((option) => {
            const IconComponent = option.icon;
            return (
              <button
                key={option.key}
                onClick={() => onSelectOption(option.description)}
                className={`
                  relative p-4 rounded-lg border-2 border-transparent
                  bg-gradient-to-r ${option.color} text-white
                  hover:shadow-lg transform hover:scale-105 transition-all duration-200
                  focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
                `}
              >
                <div className="flex items-center gap-3">
                  <div className="flex-shrink-0">
                    <IconComponent size={24} />
                  </div>
                  <div className="text-left">
                    <div className="font-medium">{option.title}</div>
                    <div className="text-sm opacity-90 mt-1">
                      기본 구조로 설계
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        <div className="flex justify-center">
          <button
            onClick={onEndConversation}
            className={`
              flex items-center gap-2 px-6 py-3 rounded-lg
              bg-gray-500 text-white hover:bg-gray-600
              transition-all duration-200
              focus:ring-2 focus:ring-offset-2 focus:ring-gray-500
            `}
          >
            <X size={18} />
            대화 종료
          </button>
        </div>
      </div>
    </div>
  );
};